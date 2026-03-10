/**
 * WSDC GitHub App — Probot webhook handler.
 *
 * Security hardening applied:
 * - OWASP A03: Input sanitization on all PR event fields
 * - OWASP A04: Error handling around Redis operations
 * - OWASP A09: Safe logging (no full payloads, no tokens)
 * - OWASP A10: Repo name format validation (prevents SSRF)
 *
 * Note: Probot handles webhook signature validation (HMAC-SHA256) internally.
 */

require("dotenv").config();
const Queue = require("bull");

// ── Input Validation (OWASP A03, A10) ──

/**
 * Validate GitHub repo full_name format (owner/repo).
 * Prevents path traversal and SSRF via crafted repository names.
 */
const REPO_NAME_REGEX = /^[a-zA-Z0-9._-]+\/[a-zA-Z0-9._-]+$/;

function validateRepoName(fullName) {
  if (!fullName || typeof fullName !== "string") return false;
  if (fullName.length > 256) return false;
  return REPO_NAME_REGEX.test(fullName);
}

/**
 * Validate a git SHA (7-40 lowercase hex characters).
 */
const GIT_SHA_REGEX = /^[0-9a-f]{7,40}$/;

function validateGitSha(sha) {
  if (!sha || typeof sha !== "string") return false;
  return GIT_SHA_REGEX.test(sha);
}

/**
 * Validate PR number is a positive integer.
 */
function validatePrNumber(num) {
  return Number.isInteger(num) && num > 0 && num <= 999999;
}

// ── Main App ──

/**
 * @param {import('probot').Probot} app
 */
module.exports = (app) => {
  app.log.info("WSDC GitHub App loaded");

  // Connect to Upstash Serverless Redis
  const redisUrl = process.env.REDIS_URL || "redis://127.0.0.1:6379";
  const prQueue = new Queue("wsdc_worker", redisUrl, {
    // Redis connection options
    redis: {
      tls: redisUrl.startsWith("rediss://") ? {} : undefined,
      maxRetriesPerRequest: 3,
    },
  });

  // Handle Redis connection errors gracefully (OWASP A04)
  prQueue.on("error", (err) => {
    app.log.error("Redis queue error: %s", err.message);
  });

  app.on(
    ["pull_request.opened", "pull_request.synchronize"],
    async (context) => {
      const pr = context.payload.pull_request;
      const repo = context.payload.repository;

      // ── Validate all inputs before processing (OWASP A03, A10) ──

      if (!validateRepoName(repo.full_name)) {
        app.log.error(
          "Rejected PR event: invalid repo name format: %s",
          String(repo.full_name).substring(0, 100)
        );
        return;
      }

      if (!validatePrNumber(pr.number)) {
        app.log.error(
          "Rejected PR event: invalid PR number for %s",
          repo.full_name
        );
        return;
      }

      if (!validateGitSha(pr.head.sha) || !validateGitSha(pr.base.sha)) {
        app.log.error(
          "Rejected PR event: invalid SHA for %s#%d",
          repo.full_name,
          pr.number
        );
        return;
      }

      // Safe logging — only identifiers (OWASP A09)
      app.log.info(`Received PR event for ${repo.full_name}#${pr.number}`);

      // Create a job for the Python Celery worker
      const jobData = {
        repo_id: repo.full_name,
        pr_number: pr.number,
        head_sha: pr.head.sha,
        base_sha: pr.base.sha,
      };

      try {
        // The name 'wsdc.process_pr_event' MUST match the @app.task name in Python Celery
        await prQueue.add("wsdc.process_pr_event", jobData, {
          attempts: 3,
          backoff: {
            type: "exponential",
            delay: 5000,
          },
          removeOnComplete: 100, // Keep last 100 completed jobs only
          removeOnFail: 50, // Keep last 50 failed jobs for debugging
        });

        app.log.info(`Enqueued job for PR #${pr.number}`);
      } catch (err) {
        // Don't crash the app on Redis failures (OWASP A04)
        app.log.error(
          "Failed to enqueue job for PR #%d: %s",
          pr.number,
          err.message
        );
        // Still post a comment so the user knows something went wrong
        const errorComment = context.issue({
          body: "⚠️ **WSDC Security Review** — Encountered an issue starting the review. Our team has been notified.",
        });
        await context.octokit.issues.createComment(errorComment);
        return;
      }

      // Leave an initial comment indicating review is in progress
      const issueComment = context.issue({
        body: "🛡️ **WSDC Security Review Started**\n\nI am currently analyzing this pull request for protocol-specific vulnerabilities. I will post my findings here shortly.",
      });
      return context.octokit.issues.createComment(issueComment);
    }
  );
};
