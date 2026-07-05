FROM node:22-slim

WORKDIR /app

# Install deps first for layer caching. npm ci installs exactly the lockfile,
# so transitive dependency drift can never break the build.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Dev server is sufficient for the take-home and keeps the reviewer's one-command
# run simple. A production image would `npm run build && npm start`.
CMD ["npm", "run", "dev"]
