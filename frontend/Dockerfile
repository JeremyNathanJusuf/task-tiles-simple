FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy the application code
COPY frontend/ .

# Expose the port
EXPOSE 3000

# Default command (can be overridden by docker-compose)
CMD ["npm", "start"] 