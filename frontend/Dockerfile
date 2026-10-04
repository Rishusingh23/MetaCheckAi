# Stage 1: Build React Application
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build production assets
RUN npm run build

# Stage 2: Serve with NGINX
FROM nginx:alpine

# Copy built assets to NGINX HTML folder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom NGINX configuration for SPA routing
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
