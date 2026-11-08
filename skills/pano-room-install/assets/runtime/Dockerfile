FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app/ /app/
ENV PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python3", "/app/server.py"]
