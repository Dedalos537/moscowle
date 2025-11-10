# Dashboard frontend Dockerfile (Vite) served by nginx
FROM nginx:stable-alpine
# Use prebuilt `build` folder from the repository to avoid running npm in the container.
COPY build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
