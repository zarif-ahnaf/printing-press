# Stage 1: Build the app
FROM node:24-alpine AS builder

WORKDIR /app

# Accept build argument
ARG PUBLIC_API_URL

# Make it available during build
ENV PUBLIC_API_URL=$PUBLIC_API_URL

# Install dependencies
COPY package*.json ./
RUN npm ci --include=dev

# Copy source code
COPY . .

# Build the app (now with PUBLIC_API_URL available)
RUN npm run build

# Stage 2: Production runtime
FROM node:24-alpine AS runner

# Create non-root user
RUN addgroup -g 1001 -S nodejs \
    && adduser -S svelte -u 1001

WORKDIR /app

# Copy build output and package files
COPY --from=builder --chown=svelte:nodejs /app/build ./build
COPY --from=builder --chown=svelte:nodejs /app/package*.json ./

# Install production deps
RUN npm ci --only=production

USER svelte

EXPOSE 3000

CMD ["node", "./build/index.js"]