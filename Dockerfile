FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY index.html .
COPY manifest.json .
COPY sw.js .

# Expose port
EXPOSE 1234

# Run the application
CMD ["python", "app.py"]
