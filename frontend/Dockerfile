# CyberSec Assistant Platform - Frontend Dockerfile
# Static HTML/JS application served with nginx

FROM nginx:alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy static files
COPY assets/ /usr/share/nginx/html/assets/
COPY pages/ /usr/share/nginx/html/pages/
COPY *.html /usr/share/nginx/html/

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]