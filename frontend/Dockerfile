FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .

# Expose port 5173 for Vite
EXPOSE 5173

# Run with --host to allow external access
CMD ["npm", "run", "dev", "--", "--host"]
