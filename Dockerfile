FROM python:3.12

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set up the FastAPI application
WORKDIR /

# Copy everything, including startup.sh
COPY . .

# Set virtual environment as the default Python environment
ARG PYTHON_ENV=/venv
ENV VIRTUAL_ENV=$PYTHON_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create virtual environment and install dependencies
RUN python -m venv $VIRTUAL_ENV && \
    . $VIRTUAL_ENV/bin/activate && \
    pip install --upgrade pip && \
    pip install --requirement requirements.txt

# Expose the FastAPI port
EXPOSE 8000

# Ensure startup.sh is executable
RUN chmod +x /startup.sh

# Run the startup shell script
CMD ["/bin/sh", "/startup.sh"]