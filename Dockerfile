FROM python:3.12

RUN apt-get update && apt-get install -y curl ffmpeg

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs

WORKDIR /

COPY . .

RUN npm ci && npm run lint && npm run type-check && npm run build

ARG PYTHON_ENV=/venv
ENV VIRTUAL_ENV=$PYTHON_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m venv $VIRTUAL_ENV && \
    . $VIRTUAL_ENV/bin/activate && \
    pip install --upgrade pip && \
    pip install --requirement requirements.txt

EXPOSE 8000

RUN chmod +x /startup.sh

CMD ["/bin/sh", "/startup.sh"]
