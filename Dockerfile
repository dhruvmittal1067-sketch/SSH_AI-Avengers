# TourConnect — container image for Cloud Run (fronted by Firebase Hosting)
FROM python:3.11-slim

# System libs needed by opencv-python-headless (video frame extraction).
# mysql-connector-python is pure Python (with an optional C extension it
# can fall back from), so no extra MySQL client libs are required here.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects $PORT (defaults to 8080) and expects the container to
# listen on it — Streamlit needs to be told explicitly, it doesn't read
# $PORT on its own.
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
EXPOSE 8080

CMD streamlit run app.py \
    --server.port=${PORT:-8080} \
    --server.address=0.0.0.0
