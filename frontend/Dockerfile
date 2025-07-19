# Etapa 1: build del frontend
FROM node:20-alpine as build

WORKDIR /app
COPY . .
RUN npm install
RUN npm run build -- --output-path=dist

# Etapa 2: servir con nginx
FROM nginx:alpine

# Copy your custom nginx.conf to the Nginx configuration directory
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built Angular app from the build stage to the Nginx web root
COPY --from=build /app/dist /usr/share/nginx/html 

# Expose port 80 for Nginx
EXPOSE 80