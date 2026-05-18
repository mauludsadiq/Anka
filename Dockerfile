FROM --platform=linux/amd64 ubuntu:22.04

RUN apt-get update && apt-get install -y curl python3 && rm -rf /var/lib/apt/lists/*

COPY fardrun /usr/local/bin/fardrun
RUN chmod +x /usr/local/bin/fardrun

WORKDIR /app
COPY anka/ anka/

RUN mkdir -p out/node

EXPOSE 18080

HEALTHCHECK --interval=5s --timeout=3s --retries=5 --start-period=10s \
  CMD curl -f http://localhost:18080/health || exit 1

CMD ["fardrun", "run", "--program", "anka/src/node_process.fard", "--out", "out/node"]
