FROM node:18-slim AS builder
WORKDIR /app
COPY shopify-app/package*.json ./
RUN npm ci
COPY shopify-app/ .
RUN npm run build

FROM node:18-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/extensions ./extensions
EXPOSE 3000
CMD ["npm", "run", "start"]
