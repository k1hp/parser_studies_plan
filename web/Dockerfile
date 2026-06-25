FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tailwind.config.js .
COPY css/tailwind.src.css css/
COPY *.html .
RUN npx tailwindcss -i css/tailwind.src.css -o css/tailwind.css -m

FROM nginx:alpine
COPY --from=builder /app/css/tailwind.css /usr/share/nginx/html/css/
COPY . /usr/share/nginx/html
EXPOSE 80
