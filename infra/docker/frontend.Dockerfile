FROM node:22-alpine

WORKDIR /app

COPY apps/frontend/package.json ./package.json
RUN npm install

COPY apps/frontend /app

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
