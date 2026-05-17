#!/bin/bash
# mesh5.sh -- Five-node local mesh for Phase 2 testing
# Ports: 18080-18084, Origin: 18090
# bash anka/mesh5.sh

GREEN="\033[0;32m"
BOLD="\033[1m"
BLUE="\033[0;34m"
RESET="\033[0m"

ok()  { echo -e "  ${GREEN}✓${RESET} $1"; }
hdr() { echo -e "\n${BOLD}${BLUE}── $1${RESET}"; }

cleanup() {
  echo -e "\n  Shutting down five-node mesh..."
  lsof -ti:18080,18081,18082,18083,18084,18085,18090 | xargs kill -9 2>/dev/null || true
  echo "  Stopped."
}
trap cleanup EXIT INT TERM

lsof -ti:18080,18081,18082,18083,18084,18085,18090 | xargs kill -9 2>/dev/null || true
sleep 1
mkdir -p out/node out/origin

hdr "Starting Origin Node (:18090)"
rm -f out/origin/anka_origin.db
fardrun run --program anka/src/origin_process.fard --out out/origin > /tmp/origin.log 2>&1 &
sleep 2
curl -s http://localhost:18090/health | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d['ok'] else 1)" \
  && ok "Origin running on :18090" || { echo "Origin failed"; exit 1; }

hdr "Starting View Node (:18085)"
mkdir -p out/view
rm -f out/view/anka_view.db
fardrun run --program anka/src/view_process.fard --out out/view > /tmp/view.log 2>&1 &
sleep 2
curl -s http://localhost:18085/health | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d['ok'] else 1)"   && ok "View node running on :18085" || echo "  View node failed"

hdr "Starting Five Nodes (:18080-18084)"
NODES=("Oxford:18080:anka_node:node_process" "MIT:18081:anka_node_b:node_process_b" "Stanford:18082:anka_node_c:node_process_c" "DeepMind:18083:anka_node_d:node_process_d" "Harvard:18084:anka_node_e:node_process_e")

PIDS=()
for entry in "${NODES[@]}"; do
  IFS=':' read -r name port db prog <<< "$entry"
  rm -f out/node/${db}.db
  python3 anka/setup.py --name "${name}-Node" --institution "$name" \
    --address "http://localhost:$port" --origin "http://localhost:18090" \
    --db out/node/${db}.db 2>/dev/null
  fardrun run --program anka/src/${prog}.fard --out out/node > /tmp/${name}.log 2>&1 &
  PIDS+=($!)
done
sleep 3

for entry in "${NODES[@]}"; do
  IFS=':' read -r name port db prog <<< "$entry"
  curl -s http://localhost:$port/health | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d['ok'] else 1)" \
    && ok "$name running on :$port" || echo "  FAILED: $name"
done

hdr "Connecting Full Mesh (all-to-all)"
PORTS=(18080 18081 18082 18083 18084)
for src in "${PORTS[@]}"; do
  for dst in "${PORTS[@]}"; do
    if [ "$src" != "$dst" ]; then
      python3 -c "import json; open('/tmp/peer_tmp.json','w').write(json.dumps({'address':'http://localhost:$dst'}))"
      curl -s -X POST http://localhost:$src/peer \
        -H "Content-Type: application/json" -d @/tmp/peer_tmp.json > /dev/null
    fi
  done
done
ok "All-to-all peer mesh established (5x4=20 connections)"

hdr "Bootstrap Registry from Origin"
for port in "${PORTS[@]}"; do
  curl -s "http://localhost:18090/registry" > /tmp/reg_tmp.json
  curl -s -X POST http://localhost:$port/registry/fetch \
    -H "Content-Type: application/json" \
    -d '{"sender_address":"http://localhost:18090"}' > /dev/null
done
ok "Registry bootstrapped on all nodes"

hdr "Registering All Nodes with View Node"
for vport in 18080 18081 18082 18083 18084; do
  python3 -c "import json; open('/tmp/vpeer.json','w').write(json.dumps({'address':f'http://localhost:$vport'}))"
  curl -s -X POST http://localhost:18085/peer -H "Content-Type: application/json" -d @/tmp/vpeer.json > /dev/null
done
curl -s -X POST http://localhost:18085/sync | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  View node synced: pulled={d["pulled"]} ingested={d["ingested_count"]}')" 2>/dev/null
ok "View node registered all five nodes as peers"

hdr "Mesh Status"
TOTAL_CLAIMS=0
for entry in "${NODES[@]}"; do
  IFS=':' read -r name port db prog <<< "$entry"
  SYNC=$(curl -s http://localhost:$port/sync)
  CLAIMS=$(echo "$SYNC" | python3 -c "import sys,json; print(json.load(sys.stdin)['claim_count'])" 2>/dev/null || echo 0)
  PEERS=$(curl -s http://localhost:$port/peers | python3 -c "import sys,json; print(len(json.load(sys.stdin)['peers']))" 2>/dev/null || echo 0)
  NODE_ID=$(curl -s http://localhost:$port/health | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'][:32])" 2>/dev/null)
  echo -e "  $name  :$port  peers=$PEERS  claims=$CLAIMS  ${NODE_ID}..."
  TOTAL_CLAIMS=$((TOTAL_CLAIMS + CLAIMS))
done

echo ""
echo -e "${BOLD}Five-node mesh running.${RESET}"
echo ""
echo "  Oxford:   http://localhost:18080"
echo "  MIT:      http://localhost:18081"
echo "  Stanford: http://localhost:18082"
echo "  DeepMind: http://localhost:18083"
echo "  Harvard:  http://localhost:18084"
echo "  Origin:   http://localhost:18090"
echo "  View:     http://localhost:18085"
echo ""
echo "Press Ctrl+C to stop."
echo ""
wait
