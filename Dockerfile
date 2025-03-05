FROM python:3.12

RUN apt-get update && apt-get install -y curl ffmpeg
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs

WORKDIR /app
COPY . .

ARG PYTHON_ENV=/app/venv
ENV VIRTUAL_ENV=$PYTHON_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m venv $VIRTUAL_ENV && \
    . $VIRTUAL_ENV/bin/activate && \
    pip install --upgrade pip && \
    pip install --requirement requirements.txt

RUN npm ci && npm run lint && npm run type-check && npm run build

RUN chmod +x /app/startup.sh

EXPOSE 8000

CMD ["/bin/sh", "/app/startup.sh"]
