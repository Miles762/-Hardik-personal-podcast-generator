FROM node:22-slim AS deps

WORKDIR /app

# Install deps first for layer caching. npm ci installs exactly the lockfile,
# so transitive dependency drift can never break the build.
COPY package.json package-lock.json ./
RUN npm ci


FROM node:22-slim AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# `public/` is optional in Next and git does not track empty dirs, so it may be
# absent in a fresh checkout. Ensure it exists so the runner COPY never fails.
RUN mkdir -p public

# Produce an optimized standalone production build (Next `output: "standalone"`).
RUN npm run build


FROM node:22-slim AS runner

WORKDIR /app
ENV NODE_ENV=production

# Copy only what the standalone server needs: the traced server, static assets,
# and public files. This keeps the runtime image small and free of dev tooling.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

# Standalone output emits its own minimal server at server.js.
CMD ["node", "server.js"]
