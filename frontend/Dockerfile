# syntax=docker/dockerfile:1

# --- Stage 1: build the React app -------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Install deps first (cached unless package files change).
COPY package.json package-lock.json ./
RUN npm ci

# Build. VITE_API_BASE_URL is baked in at build time; default "/" makes the
# app call the SAME origin, and nginx (stage 2) proxies /api -> backend. This
# keeps the backend URL out of the code and avoids CORS.
ARG VITE_API_BASE_URL=/
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY . .
RUN npm run build

# --- Stage 2: serve static files via nginx ----------------------------------
FROM nginx:alpine AS runtime

# SPA + API-proxy config (fixes /videos and /inputs refresh 404s).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Built assets only — no node_modules, no source.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# nginx:alpine already runs nginx in the foreground via its default CMD.
