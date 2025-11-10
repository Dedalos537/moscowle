# Dashboard frontend Dockerfile (Vite) served by nginx
FROM node:18-alpine AS builder
WORKDIR /app
# Copy entire context. .dockerignore should exclude node_modules if present.
COPY . .
RUN npm ci --silent || npm install --silent
RUN npm run build

FROM nginx:stable-alpine
# Vite config outputs to /app/build in this project
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
