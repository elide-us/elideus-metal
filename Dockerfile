FROM python:3.12

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set up the FastAPI application
WORKDIR /app

# Copy everything, including startup.sh
COPY . /app

# Set virtual environment as the default Python environment
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Expose the FastAPI port
EXPOSE 8000

# Ensure startup.sh is executable
RUN chmod +x /app/startup.sh

# Run the startup shell script
CMD ["/bin/sh", "/app/startup.sh"]
