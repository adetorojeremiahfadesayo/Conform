# Stage 1: Build the React frontend
FROM node:22-alpine AS web-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY app ./app
COPY data ./data
COPY --from=web-builder /web/dist ./web/dist

ENV PORT=8080
EXPOSE 8080
CMD ["python", "-m", "app.serve"]
