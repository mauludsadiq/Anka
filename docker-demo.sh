#!/bin/bash
set -e

ALICE=${ALICE:-http://localhost:18080}
BOB=${BOB:-http://localhost:18081}
ORIGIN=${ORIGIN:-http://localhost:18090}

echo ""
echo "=== ANKA Reproducibility Demo ==="
echo "Alice: $ALICE"
echo "Bob:   $BOB"
echo ""

post() {
  curl -s -X POST "$1" -H "Content-Type: application/json" --data "$2"
}

echo "=> Bootstrapping registries from origin..."
post "$ALICE/registry/fetch" '{"sender_address":"'"$ORIGIN"'"}' > /dev/null
post "$BOB/registry/fetch"   '{"sender_address":"'"$ORIGIN"'"}' > /dev/null

echo "=> Connecting Alice and Bob as peers..."
post "$ALICE/peer" '{"address":"'"$BOB"'"}' > /dev/null
post "$BOB/peer"   '{"address":"'"$ALICE"'"}' > /dev/null
echo "Mesh established"
echo ""

echo "=> Alice publishes her research finding..."
echo "   Claim space: research.result.claims"
echo "   Subject:     climate-sensitivity-2026"
echo "   Finding:     3.2C per doubling of CO2"

ALICE_DIGEST=$(post "$ALICE/publish" \
  '{"claim_space":"research.result.claims","subject":"climate-sensitivity-2026","predicate":"reported_finding","object":"3.2C per doubling of CO2","evidence_refs":["ipcc_ar7:draft","model:claude-sonnet-4"],"timestamp_unix_secs":1775710900}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['digest_hex'])")

echo "Alice published: $ALICE_DIGEST"
echo ""

sleep 3

echo "=> Bob independently replicates Alice's finding..."
echo "   Publishing to: reproducibility.results"

BOB_DIGEST=$(post "$BOB/publish" \
  '{"claim_space":"reproducibility.results","subject":"climate-sensitivity-2026","predicate":"independently_replicated","object":"confirmed:3.2C per doubling of CO2","evidence_refs":["bob_model:v2","ipcc_ar7:draft"],"timestamp_unix_secs":1775710960}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['digest_hex'])")

echo "Bob published replication: $BOB_DIGEST"
echo ""

echo "=> Bob fetching Alice's claim directly..."
curl -s -X POST "$BOB/fetch"   -H "Content-Type: application/json"   --data '{"digest_hex":"'"$ALICE_DIGEST"'","sender_address":"'"$ALICE"'","timestamp_unix_secs":1775710910}' > /dev/null
echo "   Fetch triggered"

sleep 3

echo "=> Bob witnesses Alice claim..."
curl -s -X POST "$BOB/witness"   -H "Content-Type: application/json"   --data '{"digest_hex":"'"$ALICE_DIGEST"'","witness_node_id":"bob-replication-agent","validation_type":"independent_replication","timestamp_unix_secs":1775711000}' > /dev/null
echo "   Bob witnessed"

echo "=> Pushing Bob witness back to Alice..."
curl -s -X POST "$ALICE/fetch"   -H "Content-Type: application/json"   --data '{"digest_hex":"'"$ALICE_DIGEST"'","sender_address":"'"$BOB"'","timestamp_unix_secs":1775711010}' > /dev/null
curl -s -X POST "$ALICE/witness"   -H "Content-Type: application/json"   --data '{"digest_hex":"'"$ALICE_DIGEST"'","witness_node_id":"bob-replication-agent","validation_type":"independent_replication","timestamp_unix_secs":1775711000}' > /dev/null
echo "   Witness synced to Alice"

sleep 3

echo "=> Querying the mesh (from Alice's node)..."

RESULT=$(curl -s "$ALICE/query/research.result.claims/climate-sensitivity-2026")
WINNER=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_value'])")
SCORE=$(echo "$RESULT"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_score'])")
CITE=$(echo "$RESULT"   | python3 -c "import sys,json; d=json.load(sys.stdin); w=d['single_winner']['winner_digest_hex']; print('anka:'+w) if w else print('pending')")

echo ""
echo "  Finding:  $WINNER"
echo "  Score:    $SCORE witnesses"
echo "  Cite as:  $CITE"
echo ""

REPRO=$(curl -s "$BOB/query/reproducibility.results/climate-sensitivity-2026")
REPRO_VAL=$(echo "$REPRO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['single_winner']['winner_value'])" 2>/dev/null || echo "pending")
REPRO_CITE=$(echo "$REPRO" | python3 -c "import sys,json; d=json.load(sys.stdin); print('anka:'+d['single_winner']['winner_digest_hex'])" 2>/dev/null || echo "pending")

echo "  Replication: $REPRO_VAL"
echo "  Cite as:     $REPRO_CITE"
echo ""

TRAIL=$(curl -s "$BOB/audit/trail/$ALICE_DIGEST")
PUB=$(echo "$TRAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['history']['published_count'])")
WIT=$(echo "$TRAIL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['history']['witness_count'])")

echo "  Published: $PUB event(s)"
echo "  Witnessed: $WIT event(s)"
echo "  Digest:    $ALICE_DIGEST"
echo ""

echo "=== Demo complete ==="
echo ""
echo "Alice published a research finding."
echo "Bob independently replicated it."
echo "Both results are signed, content-addressed, and queryable."
echo "The mesh converged without a central coordinator."
echo ""
echo "Alice dashboard: $ALICE/dashboard"
echo "Bob dashboard:   $BOB/dashboard"

echo ""
echo "=== Live Institution Integrations ==="
echo ""

ADAPTER=${ADAPTER:-http://adapter:19200}

echo "=> NIST: Planck constant (live from physics.nist.gov)..."
curl -s -X POST "$ADAPTER/interact" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-nist-1","actor_id":"demo","institution":"nist","intent":"What is the Planck constant?","capability":"physical_constants","context":{},"timestamp_unix_secs":1775900000}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ' + d.get('message','error'))"

echo ""
echo "=> World Bank: US GDP (live from api.worldbank.org)..."
curl -s -X POST "$ADAPTER/interact" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-wb-1","actor_id":"demo","institution":"world-bank","intent":"What is the GDP of the United States?","capability":"economic_indicator","context":{},"timestamp_unix_secs":1775900000}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ' + d.get('message','error'))"

echo ""
echo "=> Shopify: order status (live from anka-test-store.myshopify.com)..."
curl -s -X POST "$ADAPTER/interact" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-shopify-1","actor_id":"demo","institution":"the-gap","intent":"Where is my order?","capability":"order_status","context":{"order_id":"1001"},"timestamp_unix_secs":1775900000}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ' + d.get('message','error'))"

echo ""
echo "=== Live integrations complete ==="
