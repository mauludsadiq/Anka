#!/bin/bash
# anka/join.sh
# Join an existing ANKA mesh as a new node.
# Usage: bash anka/join.sh \
#          --name "MIT-Node" \
#          --institution "MIT" \
#          --address "http://mit.example.com:18080" \
#          --mesh "http://oxford.example.com:18080"

set -e

NAME=""
INSTITUTION=""
ADDRESS=""
MESH_PEER=""
PORT="18080"
DB="out/node/anka_node.db"
PROGRAM="anka/src/node_process.fard"

while [[ $# -gt 0 ]]; do
  case $1 in
    --name)        NAME="$2";        shift 2 ;;
    --institution) INSTITUTION="$2"; shift 2 ;;
    --address)     ADDRESS="$2";     shift 2 ;;
    --mesh)        MESH_PEER="$2";   shift 2 ;;
    --port)        PORT="$2";        shift 2 ;;
    --db)          DB="$2";          shift 2 ;;
    --program)     PROGRAM="$2";     shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

[ -z "$NAME" ]        && echo "Error: --name required"        && exit 1
[ -z "$INSTITUTION" ] && echo "Error: --institution required"  && exit 1
[ -z "$ADDRESS" ]     && echo "Error: --address required"      && exit 1
[ -z "$MESH_PEER" ]   && echo "Error: --mesh required"         && exit 1

GREEN="\033[0;32m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "\n${BOLD}ANKA Node Setup${RESET}"
echo "  name:        $NAME"
echo "  institution: $INSTITUTION"
echo "  address:     $ADDRESS"
echo "  joining:     $MESH_PEER"
echo ""

# 1. Discover origin from mesh peer
echo "Discovering mesh..."
ORIGIN=$(curl -s "$MESH_PEER/registry" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('origin_address', '$MESH_PEER'))
" 2>/dev/null || echo "$MESH_PEER")
echo -e "  ${GREEN}✓${RESET} Origin: $ORIGIN"

# 2. Configure node
mkdir -p $(dirname $DB)
python3 anka/setup.py \
  --name "$NAME" \
  --institution "$INSTITUTION" \
  --address "$ADDRESS" \
  --origin "$ORIGIN" \
  --peers "$MESH_PEER" \
  --db "$DB"

# 3. Start node
echo ""
echo "Starting node..."
mkdir -p out/node
fardrun run --program $PROGRAM --out out/node > /tmp/anka_join.log 2>&1 &
NODE_PID=$!
sleep 2

NODE_ID=$(curl -s "http://localhost:$PORT/health" | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])" 2>/dev/null)
[ -z "$NODE_ID" ] && echo "Node failed to start. Check /tmp/anka_join.log" && exit 1
echo -e "  ${GREEN}✓${RESET} Node running: ${NODE_ID:0:32}..."

# 4. Register with mesh peer
echo ""
echo "Registering with mesh..."
python3 -c "
import json
open('/tmp/join_peer.json','w').write(json.dumps({'address':'$ADDRESS'}))
"
curl -s -X POST "$MESH_PEER/peer" \
  -H "Content-Type: application/json" \
  -d @/tmp/join_peer.json > /dev/null

python3 -c "
import json
open('/tmp/join_peer2.json','w').write(json.dumps({'address':'$MESH_PEER'}))
"
curl -s -X POST "http://localhost:$PORT/peer" \
  -H "Content-Type: application/json" \
  -d @/tmp/join_peer2.json > /dev/null

echo -e "  ${GREEN}✓${RESET} Registered with $MESH_PEER"

# 5. Bootstrap registry from origin
SPACES=$(curl -s "$ORIGIN/registry" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('known_spaces','[]'))
" 2>/dev/null || echo "[]")
echo -e "  ${GREEN}✓${RESET} Registry bootstrapped"

# 6. Summary
MESH_CLAIMS=$(curl -s "$MESH_PEER/sync" | python3 -c "import sys,json; print(json.load(sys.stdin)['claim_count'])" 2>/dev/null || echo "?")
echo ""
echo -e "${BOLD}Joined mesh successfully.${RESET}"
echo ""
echo "  Node ID:      ${NODE_ID:0:48}..."
echo "  Mesh peer:    $MESH_PEER ($MESH_CLAIMS claims)"
echo "  Node PID:     $NODE_PID"
echo ""
echo "The node is running. To stop: kill $NODE_PID"
echo "To publish a claim: POST http://localhost:$PORT/publish"
echo ""
