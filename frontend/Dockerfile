# frontend-angular/Dockerfile
FROM node:lts-alpine3.21 AS build

WORKDIR /app
COPY . .

RUN npm install
RUN npm run build --prod

# Etapa 2: Servir con Nginx
FROM nginx:alpine

COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80

