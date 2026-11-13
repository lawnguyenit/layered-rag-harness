# Production build of the UI served by nginx. Build context is the repo root (compose sets it).
# The identity-provider and host URLs are baked in at build time (Vite env), so they are build arguments.
FROM node:22-alpine AS build
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ARG VITE_OIDC_AUTHORITY
ARG VITE_HOST_URL
ARG VITE_LOGIN_HINT=""
ENV VITE_OIDC_AUTHORITY=$VITE_OIDC_AUTHORITY VITE_HOST_URL=$VITE_HOST_URL VITE_LOGIN_HINT=$VITE_LOGIN_HINT
RUN npm run build

FROM nginx:1.27-alpine
ARG CSP_CONNECT_SRC="'self'"
COPY web/nginx.conf.template /etc/nginx/conf.d/default.conf.template
# Fill the Content-Security-Policy connect-src list from the build argument, then drop the template.
RUN sed "s|__CONNECT_SRC__|${CSP_CONNECT_SRC}|" /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf \
 && rm /etc/nginx/conf.d/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
