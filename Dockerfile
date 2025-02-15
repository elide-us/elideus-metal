# Use Python with Ubuntu
FROM python:3.12

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set up the FastAPI application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Run FastAPI
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "main:app"]
