#!/bin/sh
# ANKA node entrypoint
# Reads ANKA_NODE_NAME, ANKA_NODE_PORT, ANKA_NODE_ADDRESS from environment
# Defaults to anka-node on port 18080

NODE_NAME=${ANKA_NODE_NAME:-anka-node}
NODE_PORT=${ANKA_NODE_PORT:-18080}
NODE_ADDRESS=${ANKA_NODE_ADDRESS:-http://localhost:18080}
ORIGIN_ADDRESS=${ANKA_ORIGIN_ADDRESS:-""}
PEER_ADDRESSES=${ANKA_PEERS:-""}

echo "[anka] starting $NODE_NAME on $NODE_PORT"

# Start the node
fardrun run --program anka/src/node_process.fard --out out/node &
NODE_PID=$!
sleep 2

# Bootstrap registry from origin if configured
if [ -n "$ORIGIN_ADDRESS" ]; then
  echo "[anka] fetching registry from $ORIGIN_ADDRESS"
  curl -s -X POST http://localhost:$NODE_PORT/registry/fetch \
    -H "Content-Type: application/json" \
    -d "{\"sender_address\":\"$ORIGIN_ADDRESS\"}" > /dev/null
fi

# Register peers if configured
if [ -n "$PEER_ADDRESSES" ]; then
  for PEER in $(echo $PEER_ADDRESSES | tr "," " "); do
    echo "[anka] registering peer $PEER"
    curl -s -X POST http://localhost:$NODE_PORT/peer \
      -H "Content-Type: application/json" \
      -d "{\"address\":\"$PEER\"}" > /dev/null
  done
fi

wait $NODE_PID
