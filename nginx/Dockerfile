FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom config
COPY default.conf /etc/nginx/conf.d/

# Create a directory for SSL certs
RUN mkdir -p /etc/nginx/ssl
