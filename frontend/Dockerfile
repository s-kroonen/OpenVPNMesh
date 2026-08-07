FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/nginx.conf
COPY --chmod=755 frontend/docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 3000
CMD ["/docker-entrypoint.sh"]
