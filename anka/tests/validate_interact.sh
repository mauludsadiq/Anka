#!/bin/bash
# validate_interact.sh -- Validate an institution's ANKA interact endpoint
# Usage: bash validate_interact.sh https://agent.your-institution.com

URL="${1:-http://localhost:19100}"
GREEN="\033[0;32m"
RED="\033[0;31m"
RESET="\033[0m"

ok()  { echo -e "  ${GREEN}✓${RESET} $1"; }
err() { echo -e "  ${RED}✗${RESET} $1"; FAILED=1; }
FAILED=0

echo "Validating ANKA interact endpoint: $URL"
echo ""

echo "--- Manifest ---"
MANIFEST=$(curl -s -m 5 "$URL/manifest")
echo "$MANIFEST" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('ok'), 'ok must be true'
assert d.get('institution'), 'institution required'
assert d.get('interact_url'), 'interact_url required'
assert isinstance(d.get('capabilities'), list), 'capabilities must be list'
print('manifest valid')
" && ok "Manifest valid" || err "Manifest invalid"

echo ""
echo "--- Interact: valid request ---"
RESPONSE=$(curl -s -m 10 -X POST "$URL/interact" \
  -H "Content-Type: application/json" \
  -d @"$(dirname "$0")/interact_sample.json")
echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'ok' in d, 'ok field required'
assert 'session_id' in d, 'session_id required'
assert 'action' in d, 'action required'
assert 'message' in d, 'message required'
assert 'done' in d, 'done required'
print(f'action={d[\"action\"]} done={d[\"done\"]}')
" && ok "Interact response valid" || err "Interact response invalid"

echo ""
echo "--- Interact: unknown intent ---"
RESPONSE2=$(curl -s -m 10 -X POST "$URL/interact" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-002","actor_id":"test","institution":"test","intent":"xyzzy unknown","capability":"unknown","context":{},"timestamp_unix_secs":1775900000}')
echo "$RESPONSE2" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'ok' in d, 'ok field required'
assert 'action' in d, 'action required'
assert 'message' in d, 'message required — even for unknown intents'
print(f'action={d[\"action\"]} message_len={len(d.get(\"message\",\"\"))}')
" && ok "Unknown intent handled gracefully" || err "Unknown intent not handled"

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}All checks passed. Endpoint is ANKA interact compatible.${RESET}"
else
  echo -e "${RED}Some checks failed. See above.${RESET}"
fi
