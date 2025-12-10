# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Enable pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files
COPY apps/ops-browser/package.json apps/ops-browser/pnpm-lock.yaml* ./
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy app source
COPY apps/ops-browser ./apps/ops-browser
COPY tsconfig.json ./

# Build the app
WORKDIR /app/apps/ops-browser
RUN pnpm build

# Production stage
FROM node:20-alpine AS run

ENV NODE_ENV=production

WORKDIR /app

# Copy built files
COPY --from=build /app/apps/ops-browser/.next/standalone ./
COPY --from=build /app/apps/ops-browser/.next/static ./apps/ops-browser/.next/static
COPY --from=build /app/apps/ops-browser/public ./apps/ops-browser/public

ENV PORT=3000
EXPOSE 3000

CMD ["node", "apps/ops-browser/server.js"]











