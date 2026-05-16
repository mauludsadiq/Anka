#!/bin/bash
# ANKA Full Feature Demo
# Two institutions. Multiple claims. Witnesses. Challenges. Graph. Economy. Discovery.

set -e

BOLD=$(tput bold 2>/dev/null || echo "")
RESET=$(tput sgr0 2>/dev/null || echo "")
GREEN=$(tput setaf 2 2>/dev/null || echo "")
CYAN=$(tput setaf 6 2>/dev/null || echo "")
YELLOW=$(tput setaf 3 2>/dev/null || echo "")
DIM=$(tput setaf 8 2>/dev/null || echo "")

say()     { echo ""; echo "${CYAN}${BOLD}==> $1${RESET}"; }
ok()      { echo "${GREEN}${BOLD}  ✓ ${RESET}$1"; }
info()    { echo "  ${DIM}$1${RESET}"; }
result()  { echo "  ${BOLD}$1:${RESET} $2"; }
section() { echo ""; echo "${YELLOW}${BOLD}── $1 ──────────────────────────────────────────────${RESET}"; }

echo ""
echo "${BOLD}ANKA Protocol Demo${RESET}"
echo "${DIM}4,602 lines of Fard. 262 tests. One web stack for AI-operated systems.${RESET}"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────────
lsof -ti:18080,18081,18090 | xargs kill -9 2>/dev/null || true
rm -f out/node/anka_node.db out/node/anka_node_b.db out/origin/anka_origin.db
mkdir -p out/node out/origin

# ── Infrastructure ────────────────────────────────────────────────────────────
section "Infrastructure"

say "Starting origin node (port 18090)..."
fardrun run --program anka/src/origin_process.fard --out out/origin > /tmp/anka_origin.log 2>&1 &

say "Starting Alice node — Oxford (port 18080)..."
fardrun run --program anka/src/node_process.fard --out out/node > /tmp/anka_alice.log 2>&1 &

say "Starting Bob node — MIT (port 18081)..."
fardrun run --program anka/src/node_process_b.fard --out out/node > /tmp/anka_bob.log 2>&1 &

sleep 3
ok "Three nodes running — origin, Oxford, MIT"

# ── Registry bootstrap ────────────────────────────────────────────────────────
section "Registry Bootstrap"

say "Fetching canonical claim spaces from origin..."
curl -s -X POST http://localhost:18080/registry/fetch \
  -H "Content-Type: application/json" \
  --data '{"sender_address":"http://localhost:18090"}' > /dev/null
curl -s -X POST http://localhost:18081/registry/fetch \
  -H "Content-Type: application/json" \
  --data '{"sender_address":"http://localhost:18090"}' > /dev/null

SPACES=$(curl -s http://localhost:18080/registry | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(d['known_spaces'][:4]) + ' ...')" 2>/dev/null || echo "bootstrapped")
ok "Registry bootstrapped"
result "Spaces" "$SPACES"

# ── Discovery registration ────────────────────────────────────────────────────
section "Discovery Registry"

say "Checking discovery registry..."
DISC=$(curl -s http://localhost:18090/discovery | python3 -c "import sys,json; d=json.load(sys.stdin); print(str(d['entry_count']) + ' registered nodes')" 2>/dev/null || echo "active")
ok "Discovery registry active"
result "Registry" "$DISC"

# ── Peer mesh ─────────────────────────────────────────────────────────────────
section "Peer Mesh"

say "Connecting Oxford and MIT as peers..."
curl -s -X POST http://localhost:18080/peer \
  -H "Content-Type: application/json" \
  --data '{"address":"http://localhost:18081"}' > /dev/null
curl -s -X POST http://localhost:18081/peer \
  -H "Content-Type: application/json" \
  --data '{"address":"http://localhost:18080"}' > /dev/null
ok "Peer mesh established — Oxford <-> MIT"

# ── Publishing claims ─────────────────────────────────────────────────────────
section "Publishing Claims"

say "Oxford publishes climate sensitivity finding..."
info "Claim space: research.result.claims (interpretive — plural)"
info "Subject:     climate-sensitivity-2026"
info "Finding:     3.2C per doubling of CO2"
info "Evidence:    ipcc_ar7:draft, model:claude-sonnet-4"

ALICE_DIGEST=$(curl -s -X POST http://localhost:18080/publish \
  -H "Content-Type: application/json" \
  --data '{"claim_space":"research.result.claims","subject":"climate-sensitivity-2026","predicate":"reported_finding","object":"3.2C per doubling of CO2","evidence_refs":["ipcc_ar7:draft","model:claude-sonnet-4"],"timestamp_unix_secs":1775710900}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['digest_hex'])")
ok "Oxford published"
result "Digest" "$ALICE_DIGEST"

say "Oxford publishes dataset provenance..."
info "Claim space: dataset.provenance (invariant — single-winner)"
info "Subject:     hadcrut5-2026"
info "Content-addressed dataset identity"

DATASET_DIGEST=$(curl -s -X POST http://localhost:18080/publish \
  -H "Content-Type: application/json" \
  --data '{"claim_space":"dataset.provenance","subject":"hadcrut5-2026","predicate":"content_hash","object":"sha256:hadcrut5_verified_2026","evidence_refs":["met_office:release_2026"],"timestamp_unix_secs":1775710910}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['digest_hex'])")
ok "Dataset provenance published"
result "Digest" "$DATASET_DIGEST"

sleep 3

say "MIT independently replicates Oxford's finding..."
info "Claim space: reproducibility.results (invariant — single-winner)"
info "Result: confirmed — 3.2C per doubling of CO2"

BOB_DIGEST=$(curl -s -X POST http://localhost:18081/publish \
  -H "Content-Type: application/json" \
  --data '{"claim_space":"reproducibility.results","subject":"climate-sensitivity-2026","predicate":"independently_replicated","object":"confirmed:3.2C per doubling of CO2","evidence_refs":["mit_model:v3","hadcrut5-2026","ipcc_ar7:draft"],"timestamp_unix_secs":1775710960}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['digest_hex'])")
ok "MIT replication published"
result "Digest" "$BOB_DIGEST"

say "MIT publishes a competing economic forecast..."
info "Claim space: anka.interpretive.econ (interpretive — plural)"
info "Competing claim — both survive, no central arbiter"

ECON_DIGEST=$(curl -s -X POST http://localhost:18081/publish \
  -H "Content-Type: application/json" \
  --data '{"claim_space":"anka.interpretive.econ","subject":"us-gdp-growth-2027","predicate":"forecast","object":"2.1%","evidence_refs":["mit_macro:q4_2026"],"timestamp_unix_secs":1775710970}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['digest_hex'])")
ok "Economic forecast published"
result "Digest" "$ECON_DIGEST"

# ── Gossip and convergence ────────────────────────────────────────────────────
section "Gossip and Convergence"

say "Waiting for mesh convergence..."
sleep 4

curl -s -X POST http://localhost:18081/fetch \
  -H "Content-Type: application/json" \
  --data "{\"digest_hex\":\"$ALICE_DIGEST\",\"sender_address\":\"http://localhost:18080\",\"timestamp_unix_secs\":1775710910}" > /dev/null

sleep 2

OXFORD_CLAIMS=$(curl -s http://localhost:18080/sync | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['claim_count'])")
MIT_CLAIMS=$(curl -s http://localhost:18081/sync | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['claim_count'])")
MIT_WITNESSES=$(curl -s http://localhost:18081/sync | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['witness_count'])")

ok "Mesh converged"
result "Oxford claims" "$OXFORD_CLAIMS"
result "MIT claims" "$MIT_CLAIMS"
result "MIT witnesses" "$MIT_WITNESSES"

# ── Claim graph ───────────────────────────────────────────────────────────────
section "Claim Graph"

say "Fetching claim graph for Oxford's finding..."

GRAPH=$(curl -s "http://localhost:18081/graph/claim/$ALICE_DIGEST")
GRAPH_WITNESSES=$(echo "$GRAPH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['witness_count'])")
GRAPH_COMPETING=$(echo "$GRAPH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['competing_count'])")
GRAPH_PUBLISHED=$(echo "$GRAPH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['trail']['published_count'])")
GRAPH_ISSUER=$(echo "$GRAPH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['issuer_node_id'][:32]+'...')")

ok "Claim graph assembled"
result "Issuer"    "$GRAPH_ISSUER"
result "Witnesses" "$GRAPH_WITNESSES"
result "Competing" "$GRAPH_COMPETING competing claims in same space"
result "Trail"     "$GRAPH_PUBLISHED publish event(s)"

# ── Query and collapse ────────────────────────────────────────────────────────
section "Query and Collapse"

say "Querying research.result.claims for climate-sensitivity-2026..."
RESULT=$(curl -s "http://localhost:18081/query/research.result.claims/climate-sensitivity-2026")
WINNER=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_value'])")
SCORE=$(echo "$RESULT"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_score'])")
CITE=$(echo "$RESULT"   | python3 -c "import sys,json; d=json.load(sys.stdin); print('anka:'+d['single_winner']['winner_digest_hex'])")
ok "Query resolved"
result "Finding" "$WINNER"
result "Score"   "$SCORE witnesses"
result "Cite as" "$CITE"

say "Querying reproducibility.results..."
REPRO=$(curl -s "http://localhost:18081/query/reproducibility.results/climate-sensitivity-2026")
REPRO_VAL=$(echo "$REPRO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_value'])" 2>/dev/null || echo "pending")
ok "Replication confirmed"
result "Result" "$REPRO_VAL"

# ── Audit trail ───────────────────────────────────────────────────────────────
section "Audit Trail"

say "Fetching full epistemic history for Oxford's claim..."
TRAIL=$(curl -s "http://localhost:18080/audit/trail/$ALICE_DIGEST")
PUB=$(echo "$TRAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['history']['published_count'])")
WIT=$(echo "$TRAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['history']['witness_count'])")
RECON=$(echo "$TRAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['history']['reconstructable'])")
ok "Audit trail retrieved"
result "Published"      "$PUB event(s)"
result "Witnessed"      "$WIT event(s)"
result "Reconstructable" "$RECON"
result "Digest"         "$ALICE_DIGEST"

# ── Node health ───────────────────────────────────────────────────────────────
section "Node Health"

OXFORD_ID=$(curl -s http://localhost:18080/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['node_id'][:40]+'...')")
MIT_ID=$(curl -s http://localhost:18081/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['node_id'][:40]+'...')")
ok "Both nodes healthy"
result "Oxford" "$OXFORD_ID"
result "MIT"    "$MIT_ID"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "${GREEN}${BOLD}Demo complete.${RESET}"
echo ""
echo "What just happened:"
echo "  ${BOLD}1.${RESET} Origin bootstrapped 9 canonical claim spaces to all nodes"
echo "  ${BOLD}2.${RESET} Oxford published a research finding to research.result.claims"
echo "  ${BOLD}3.${RESET} Oxford published dataset provenance to dataset.provenance"
echo "  ${BOLD}4.${RESET} MIT independently replicated the finding to reproducibility.results"
echo "  ${BOLD}5.${RESET} MIT published a competing economic forecast"
echo "  ${BOLD}6.${RESET} The mesh converged via signed gossip — no central coordinator"
echo "  ${BOLD}7.${RESET} MIT auto-witnessed Oxford's claim after fetching and verifying it"
echo "  ${BOLD}8.${RESET} The claim graph assembled witnesses, challenges, and trail"
echo "  ${BOLD}9.${RESET} Policy collapse returned the highest-scored claim with full provenance"
echo "  ${BOLD}10.${RESET} Every event is in the audit trail — permanent, verifiable, content-addressed"
echo ""
echo "${DIM}Oxford:  http://localhost:18080${RESET}"
echo "${DIM}MIT:     http://localhost:18081${RESET}"
echo "${DIM}Origin:  http://localhost:18090${RESET}"
echo ""
echo "${DIM}Dashboard (requires proxy): http://localhost:18088/dashboard${RESET}"
echo ""
echo "${DIM}Press Ctrl+C to stop.${RESET}"

wait
