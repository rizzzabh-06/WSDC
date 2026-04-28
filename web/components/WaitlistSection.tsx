"use client";

import { useState, type FormEvent } from "react";
import { supabase } from "@/lib/supabase";

type SubmitState = "idle" | "submitting" | "success" | "error";

export default function WaitlistSection() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [state, setState] = useState<SubmitState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setState("submitting");
    setErrorMsg("");

    try {
      if (!supabase) {
        throw new Error("Waitlist is being set up. Please try again shortly.");
      }

      const { error } = await supabase.from("waitlist").insert([
        {
          email: email.trim().toLowerCase(),
          name: name.trim() || null,
          role: role || null,
          source: "website",
        },
      ]);

      if (error) {
        // Duplicate email
        if (error.code === "23505") {
          setState("success");
          return;
        }
        throw error;
      }

      setState("success");
      setEmail("");
      setName("");
      setRole("");
    } catch (err: unknown) {
      setState("error");
      setErrorMsg(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    }
  };

  return (
    <section id="waitlist" className="section-padding relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/5 text-xs font-medium text-accent-glow mb-4">
            EARLY ACCESS
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            Get Early Access
          </h2>
          <p className="max-w-xl mx-auto text-text-secondary">
            WSDC is currently in private beta. Join the waitlist to be among the first to
            secure your development workflow with AI-powered reviews.
          </p>
        </div>

        {/* Form card */}
        <div className="glass-card rounded-2xl p-8 sm:p-10" style={{ animation: "none" }}>
          {state === "success" ? (
            <div className="text-center py-6" style={{ animation: "fade-in 0.4s ease-out" }}>
              <div className="w-16 h-16 rounded-2xl bg-accent-green/10 border border-accent-green/20 flex items-center justify-center mx-auto mb-4">
                <svg
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-accent-green"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-text-primary mb-2">
                You&apos;re on the list!
              </h3>
              <p className="text-sm text-text-secondary max-w-sm mx-auto">
                We&apos;ll reach out when your spot is ready. In the meantime, check out
                the demo above to see what&apos;s coming.
              </p>
              <button
                onClick={() => setState("idle")}
                className="mt-6 text-sm text-accent-glow hover:text-accent-bright transition-colors"
              >
                Submit another response
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Name + Email row */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="waitlist-name"
                    className="block text-sm font-medium text-text-secondary mb-1.5"
                  >
                    Name
                  </label>
                  <input
                    id="waitlist-name"
                    type="text"
                    placeholder="Alex Chen"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-background border border-border text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/25 transition-colors"
                  />
                </div>
                <div>
                  <label
                    htmlFor="waitlist-email"
                    className="block text-sm font-medium text-text-secondary mb-1.5"
                  >
                    Email <span className="text-accent-red">*</span>
                  </label>
                  <input
                    id="waitlist-email"
                    type="email"
                    required
                    placeholder="alex@protocol.xyz"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-background border border-border text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/25 transition-colors"
                  />
                </div>
              </div>

              {/* Role dropdown */}
              <div>
                <label
                  htmlFor="waitlist-role"
                  className="block text-sm font-medium text-text-secondary mb-1.5"
                >
                  What best describes you?
                </label>
                <select
                  id="waitlist-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-background border border-border text-sm text-text-primary focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/25 transition-colors appearance-none"
                  style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")`,
                    backgroundRepeat: "no-repeat",
                    backgroundPosition: "right 12px center",
                  }}
                >
                  <option value="">Select a role...</option>
                  <option value="protocol_engineer">Protocol / Smart Contract Engineer</option>
                  <option value="security_lead">Security Lead / Auditor</option>
                  <option value="engineering_manager">Engineering Manager</option>
                  <option value="founder">Founder / CTO</option>
                  <option value="developer">Web3 Developer</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Error message */}
              {state === "error" && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-accent-red/5 border border-accent-red/20 text-sm text-accent-red">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                  {errorMsg}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={state === "submitting" || !email}
                className="w-full px-6 py-3.5 rounded-xl bg-accent hover:bg-accent-glow text-white font-semibold text-sm transition-all duration-300 hover:shadow-lg hover:shadow-accent/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {state === "submitting" ? (
                  <>
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="animate-spin"
                    >
                      <circle
                        cx="12"
                        cy="12"
                        r="10"
                        strokeDasharray="31.4"
                        strokeDashoffset="10"
                      />
                    </svg>
                    Joining...
                  </>
                ) : (
                  <>
                    Join the Waitlist
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </>
                )}
              </button>

              <p className="text-xs text-text-muted text-center">
                No spam, ever. We&apos;ll only contact you about WSDC access.
              </p>
            </form>
          )}
        </div>

        {/* Social proof */}
        <div className="mt-8 flex items-center justify-center gap-6 text-sm text-text-muted">
          <div className="flex items-center gap-2">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-accent-green"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Free during beta
          </div>
          <div className="flex items-center gap-2">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-accent-green"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            5-minute setup
          </div>
          <div className="flex items-center gap-2">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-accent-green"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Cancel anytime
          </div>
        </div>
      </div>
    </section>
  );
}
