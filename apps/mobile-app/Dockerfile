# Dockerfile for building and serving StudyBot Mobile (Expo) in a CI environment.
# This is primarily for running tests, type-checking, and linting.
# For actual mobile builds, use EAS Build (expo.dev) or local Xcode/Android Studio.

FROM node:20-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy package files first for better layer caching
COPY package.json ./
RUN npm install

# Copy the rest of the app
COPY . .

# Type-check
RUN npx tsc --noEmit

# Expose Expo dev server port
EXPOSE 8081

# Default command: start Expo in tunnel mode for remote development
CMD ["npx", "expo", "start", "--tunnel"]
