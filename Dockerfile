# OrbitDesk – ein Container für Backend und Oberfläche.
#
# Stufe 1 baut das React-Frontend zu statischen Dateien (HTML/JS/CSS).
# Stufe 2 enthält nur Python + Backend + die gebauten Dateien. Node.js wird
# im fertigen Container nicht mehr gebraucht, das hält ihn klein.

# ---------- Stufe 1: Frontend bauen ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Stufe 2: Backend ----------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ORBITDESK_DATA_DIR=/data \
    ORBITDESK_STATIC_DIR=/app/static
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/dist ./static
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
