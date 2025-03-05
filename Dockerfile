# Stage 1: Build React assets with Node
FROM node:18 AS react-build
WORKDIR /app
# Copy only what’s needed for the React build (adjust if your repo structure is different)
COPY package*.json ./
RUN npm ci
# Now copy the rest of your source (including your React code)
COPY . .
# Run lint, type-check, and build
RUN npm run lint && npm run type-check && npm run build
# At this point, the build output is generated.
# Assuming your React build outputs to a folder named "static" in /app

# Stage 2: Build the final image with Python
FROM python:3.12
# Install system dependencies (curl, ffmpeg) and Node if needed
RUN apt-get update && apt-get install -y curl ffmpeg
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs

WORKDIR /app
# Copy your entire repository (backend and source code)
COPY . .
# Overwrite (or add) the built React assets from the previous stage
COPY --from=react-build /app/static /app/static

# Set up the Python virtual environment
ARG PYTHON_ENV=/app/venv
ENV VIRTUAL_ENV=$PYTHON_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python -m venv $VIRTUAL_ENV && \
    . $VIRTUAL_ENV/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Ensure startup.sh is executable
RUN chmod +x /app/startup.sh

EXPOSE 8000
CMD ["/bin/sh", "/app/startup.sh"]
