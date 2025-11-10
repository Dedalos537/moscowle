# Frontend Dockerfile - Principal_Page (Vite)
FROM nginx:stable-alpine
# Use prebuilt `build` folder from the repository to avoid running npm in the container.
COPY build /usr/share/nginx/html
# Copy a basic nginx conf to enable SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
