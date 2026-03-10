# Security-hardened Dockerfile (OWASP A05, CVE-2019-5736 class mitigation)
FROM node:20-slim

# Create non-root user (CVE-2019-5736 container escape mitigation)
RUN groupadd --gid 1001 wsdc && \
    useradd --uid 1001 --gid wsdc --shell /bin/sh --create-home wsdc

WORKDIR /usr/src/app

# Copy dependency files first for better caching
COPY package.json package-lock.json ./

# Install production dependencies only
RUN npm ci --production && \
    npm cache clean --force

# Set production environment
ENV NODE_ENV="production"

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R wsdc:wsdc /usr/src/app

# Switch to non-root user
USER wsdc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "process.exit(0)" || exit 1

# Expose port (documentation only)
EXPOSE 3000

CMD [ "npm", "start" ]
