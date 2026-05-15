#!/bin/bash
# ANKA Alice/Bob Reproducibility Demo
# Two researchers. One claim. Independent replication. Verifiable result.

set -e

BOLD=$(tput bold 2>/dev/null || echo "")
RESET=$(tput sgr0 2>/dev/null || echo "")
GREEN=$(tput setaf 2 2>/dev/null || echo "")
CYAN=$(tput setaf 6 2>/dev/null || echo "")
DIM=$(tput setaf 8 2>/dev/null || echo "")

say() { echo "${CYAN}${BOLD}=> ${RESET}$1"; }
ok()  { echo "${GREEN}${BOLD}✓ ${RESET}$1"; }
dim() { echo "  ${DIM}$1${RESET}"; }

echo ""
echo "${BOLD}ANKA Reproducibility Demo${RESET}"
echo "${DIM}Two researchers. One claim. Independent replication.${RESET}"
echo ""

lsof -ti:18080,18081,18090 | xargs kill -9 2>/dev/null || true
rm -f out/node/anka_node.db out/node/anka_node_b.db out/origin/anka_origin.db
mkdir -p out/node out/origin

say "Starting origin node..."
fardrun run --program anka/src/origin_process.fard --out out/origin > /tmp/anka_origin.log 2>&1 &

say "Starting Alice node (port 18080)..."
fardrun run --program anka/src/node_process.fard --out out/node > /tmp/anka_alice.log 2>&1 &

say "Starting Bob node (port 18081)..."
fardrun run --program anka/src/node_process_b.fard --out out/node > /tmp/anka_bob.log 2>&1 &

sleep 3
ok "All nodes running"
echo ""

say "Bootstrapping registries from origin..."
curl -s -X POST http://localhost:18080/registry/fetch   -H "Content-Type: application/json"   --data '{"sender_address":"http://localhost:18090"}' > /dev/null
curl -s -X POST http://localhost:18081/registry/fetch   -H "Content-Type: application/json"   --data '{"sender_address":"http://localhost:18090"}' > /dev/null

say "Connecting Alice and Bob as peers..."
curl -s -X POST http://localhost:18080/peer   -H "Content-Type: application/json"   --data '{"address":"http://localhost:18081"}' > /dev/null
curl -s -X POST http://localhost:18081/peer   -H "Content-Type: application/json"   --data '{"address":"http://localhost:18080"}' > /dev/null
ok "Mesh established"
echo ""

say "Alice publishes her research finding..."
dim "Claim space: research.result.claims"
dim "Subject:     climate-sensitivity-2026"
dim "Finding:     3.2C per doubling of CO2"
dim "Evidence:    ipcc_ar7:draft, model:claude-sonnet-4"

ALICE_DIGEST=$(curl -s -X POST http://localhost:18080/publish   -H "Content-Type: application/json"   --data '{"claim_space":"research.result.claims","subject":"climate-sensitivity-2026","predicate":"reported_finding","object":"3.2C per doubling of CO2","evidence_refs":["ipcc_ar7:draft","model:claude-sonnet-4"],"timestamp_unix_secs":1775710900}'   | python3 -c "import sys,json; print(json.load(sys.stdin)[chr(100)+chr(105)+chr(103)+chr(101)+chr(115)+chr(116)+chr(95)+chr(104)+chr(101)+chr(120)])")

ok "Alice published: ${DIM}${ALICE_DIGEST}${RESET}"
echo ""

sleep 3

say "Bob independently replicates Alice's finding..."
dim "Bob runs his own climate model with the same inputs"
dim "Result: confirmed — 3.2C per doubling of CO2"
dim "Publishing to: reproducibility.results"

BOB_DATA='{"claim_space":"reproducibility.results","subject":"climate-sensitivity-2026","predicate":"independently_replicated","object":"confirmed:3.2C per doubling of CO2","evidence_refs":["bob_model:v2","ipcc_ar7:draft"],"timestamp_unix_secs":1775710960}'

BOB_DIGEST=$(curl -s -X POST http://localhost:18081/publish   -H "Content-Type: application/json"   --data "$BOB_DATA"   | python3 -c "import sys,json; print(json.load(sys.stdin)['digest_hex'])")

ok "Bob published replication: ${DIM}${BOB_DIGEST}${RESET}"
echo ""

sleep 4

say "Querying the mesh for Alice's finding..."
echo ""

RESULT=$(curl -s "http://localhost:18081/query/research.result.claims/climate-sensitivity-2026")
WINNER=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_value'])")
SCORE=$(echo "$RESULT"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_score'])")
COUNT=$(echo "$RESULT"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['claim_count'])")
CITE="anka:$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_digest_hex'])")"

echo "  ${BOLD}Finding:${RESET}  $WINNER"
echo "  ${BOLD}Score:${RESET}    $SCORE witnesses"
echo "  ${BOLD}Claims:${RESET}   $COUNT in this space"
echo "  ${BOLD}Cite as:${RESET}  $CITE"
echo ""

say "Querying Bob's replication result..."
echo ""

REPRO=$(curl -s "http://localhost:18081/query/reproducibility.results/climate-sensitivity-2026")
REPRO_VAL=$(echo "$REPRO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_value'])" 2>/dev/null || echo "pending")
REPRO_CITE="anka:$(echo "$REPRO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_digest_hex'])" 2>/dev/null || echo "pending")"

echo "  ${BOLD}Replication:${RESET} $REPRO_VAL"
echo "  ${BOLD}Cite as:${RESET}     $REPRO_CITE"
echo ""

say "Fetching audit trail for Alice's claim..."
TRAIL=$(curl -s "http://localhost:18081/audit/trail/${ALICE_DIGEST}")
PUB=$(echo "$TRAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['history']['published_count'])")
WIT=$(echo "$TRAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['history']['witness_count'])")

echo "  ${BOLD}Published:${RESET} $PUB event(s)"
echo "  ${BOLD}Witnessed:${RESET} $WIT event(s)"
echo "  ${BOLD}Digest:${RESET}    $ALICE_DIGEST"
echo ""

echo "${GREEN}${BOLD}Demo complete.${RESET}"
echo ""
echo "Alice published a research finding."
echo "Bob independently replicated it."
echo "Both results are signed, content-addressed, and queryable."
echo "The mesh converged without a central coordinator."
echo ""
echo "${DIM}Alice: http://localhost:18080${RESET}"
echo "${DIM}Bob:   http://localhost:18081${RESET}"
echo ""
echo "${DIM}Press Ctrl+C to stop nodes.${RESET}"

wait
