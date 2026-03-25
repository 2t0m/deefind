FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for deemix
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY index.html .
COPY styles.css .
COPY app.js .
COPY manifest.json .
COPY sw.js .

# Expose port
EXPOSE 1234

# Run the application
CMD ["python", "app.py"]
