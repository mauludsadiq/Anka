FROM --platform=linux/amd64 debian:bookworm-slim

RUN apt-get update && apt-get install -y curl ca-certificates sqlite3 python3 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://github.com/mauludsadiq/FARD/releases/download/v1.6.1/fardrun-linux-x86_64     -o /usr/local/bin/fardrun && chmod +x /usr/local/bin/fardrun

WORKDIR /anka
COPY anka/ ./anka/
COPY docker-demo.sh /anka/docker-demo.sh
COPY docker-entrypoint.sh /anka/docker-entrypoint.sh
COPY docker-demo.sh /anka/docker-demo.sh
COPY docker-entrypoint.sh /anka/docker-entrypoint.sh
COPY docker-demo.sh /anka/docker-demo.sh
COPY docker-entrypoint.sh /anka/docker-entrypoint.sh

RUN mkdir -p out/node out/origin out/policy

EXPOSE 18080 18081 18082 18083 18084 18090

ENV ANKA_NODE_NAME=anka-node
ENV ANKA_NODE_PORT=18080
ENV ANKA_NODE_ADDRESS=http://localhost:18080

CMD fardrun run --program anka/src/node_process.fard --out out/node
