# WSDC Local Development Guide

Since we are using a **Serverless Foundation** (Upstash Redis + Neon Postgres), we do not need Docker locally. You simply run the Node and Python apps natively.

## 1. Prerequisites

You must set up the following free-tier services:
1. **Upstash Redis**: Get a serverless REDIS_URL from [Upstash](https://upstash.com)
2. **Neon Postgres**: Get a serverless DATABASE_URL from [Neon](https://neon.tech)
3. **Smee.io**: Go to [smee.io](https://smee.io) and click "Start a new channel". Copy the URL.
4. **GitHub App**: Register a GitHub app locally and give it Pull Request Read/Write permissions. Point its webhook URL to your smee.io URL.

Copy the `.env.example` to `.env` in the root of the monorepo and fill in the values.

## 2. Installation

Run the installation script to set up Node modules and the Python Virtual Environment:
```bash
make install
```

## 3. Running the Services

To run WSDC locally, you'll need three separate terminal tabs. Run one command per tab:

### Tab 1: Start GitHub App
```bash
make start-github-app
```

### Tab 2: Start API Server
```bash
make start-backend
```

### Tab 3: Start Celery Worker
```bash
make start-worker
```

## 4. End-to-End Testing

Once everything is running, open a Pull Request in a repository where your GitHub App is installed. 
1. The GitHub App (Tab 1) should log that it received a `pull_request.opened` event and enqueued it to Upstash.
2. The Celery Worker (Tab 3) should log that it picked up the PR event from Upstash.
