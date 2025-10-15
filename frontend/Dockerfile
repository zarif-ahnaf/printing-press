# Stage 1: Build the app
FROM node:24-alpine AS builder

WORKDIR /app

# Install dependencies (including dev deps needed for build)
COPY package*.json ./
RUN npm ci --include=dev

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Stage 2: Production runtime
FROM node:24-alpine AS runner

# Create a non-root user for security
RUN addgroup -g 1001 -S nodejs \
    && adduser -S svelte -u 1001

WORKDIR /app

# Copy only the production build and package files
COPY --from=builder --chown=svelte:nodejs /app/build ./build
COPY --from=builder --chown=svelte:nodejs /app/package*.json ./

# Install only production dependencies
RUN npm ci --only=production

# Switch to non-root user
USER svelte

# SvelteKit (with adapter-node or adapter-auto in Node mode) uses port 3000 by default
EXPOSE 3000

# Start the server
CMD ["node", "./build/index.js"]