# syntax=docker/dockerfile:1
#
# Frontend image for the ClinicDesk dashboard.
#
# Multi-stage: Node builds the Vite bundle, then only the static output is
# copied into an nginx runtime. No node_modules, no npm cache and no build
# tooling in the final image, which is both smaller and safer to scan.

# ---------- Stage 1: build the bundle ----------
FROM node:22-alpine AS builder

WORKDIR /build

# Copy the manifest first so `npm ci` is cached and only re-runs when the
# dependency lockfile changes, not on every source edit.
COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.js ./
COPY src ./src

RUN npm run build

# ---------- Stage 2: nginx runtime ----------
FROM nginx:1.27-alpine AS runtime

# nginx:alpine ships an nginx user (uid 101) already.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

# The stock entrypoint writes its pid to /run/nginx.pid and rewrites
# conf.d/default.conf, so both must belong to nginx. /var/run is a symlink to
# /run in Alpine, so chown /run directly.
RUN chown -R nginx:nginx /run /var/cache/nginx /var/log/nginx /etc/nginx/conf.d \
    && chown -R nginx:nginx /usr/share/nginx/html \
    && touch /run/nginx.pid && chown nginx:nginx /run/nginx.pid

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]