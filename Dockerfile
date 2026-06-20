FROM python:3.10-slim

WORKDIR /workspace

# Install system dependencies needed for compiling python tools if any (lightweight)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app/ ./app/

# Expose Streamlit default port
EXPOSE 8503

# Configure Streamlit environment variables
ENV STREAMLIT_SERVER_PORT=8503
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Run the app
CMD ["streamlit", "run", "app/main.py"]
