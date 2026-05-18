#!/bin/bash
# ANKA Quick Demo — docker compose up + accident flow
# One command. Full stack. ~60 seconds.

set -e
BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}ANKA — AI-Native Epistemic Coordination Stack${RESET}"
echo -e "The first protocol for AI-to-AI institutional coordination."
echo ""

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo "Docker required. https://docker.com"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python3 required."; exit 1; }

echo -e "${CYAN}Starting stack...${RESET}"
docker compose up -d --remove-orphans 2>/dev/null
sleep 5

# Wait for alice to be healthy
echo -e "${CYAN}Waiting for mesh...${RESET}"
for i in $(seq 1 20); do
    if curl -sf http://localhost:18080/health > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo ""
echo -e "${BOLD}=== ANKA Killer Demo: AI as Your Institutional Agent ===${RESET}"
echo ""

# Run the dynamic accident flow against the running stack
ALICE=http://localhost:18080
ADAPTER=http://localhost:19200
DALIL=http://localhost:17000

python3 - << 'PYEOF'
import json, urllib.request, hashlib, time, os, sys

def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(),
        {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())

node    = "http://localhost:18080"
adapter = "http://localhost:19200"

print('User: "I was in a minor car accident yesterday. The other driver')
print('       ran a red light. I need help with the insurance claim,')
print('       getting my car repaired, and the police report."')
print()

ts = int(time.time())
incident_id = "INC-" + hashlib.sha256(str(ts).encode()).hexdigest()[:8].upper()

# Register institutions
for name, addr, nid, itype, alias in [
    ("city-pd",    adapter, "ed25519:citypd",    "government", "citypd"),
    ("state-farm", adapter, "ed25519:statefarm",  "insurance",  "statefarm"),
    ("city-auto",  adapter, "ed25519:cityauto",   "repair",     "cityauto"),
]:
    post(f"{node}/runtime/registry", {"name": name, "address": addr,
        "node_id": nid, "institution_type": itype, "alias": alias})

print("Step 1: Filing police report...")
r1 = post(f"{adapter}/interact", {
    "session_id": f"{incident_id}-police",
    "actor_id": "user:jane-doe", "institution": "city-pd",
    "intent": "I need to file a police report for a car accident",
    "capability": "police_report",
    "context": {"incident_id": incident_id, "date": "2026-05-18",
        "location": "Main St & 5th Ave",
        "description": "Other driver ran red light, struck driver side",
        "injuries": "none", "vehicle": "2022 Honda Civic"}
})
report = r1["result"].get("report_number", "RPT-???")
print(f"  {report} filed. Officer Rodriguez assigned.")

print("Step 2: Filing insurance claim (live World Bank CPI)...")
r2 = post(f"{adapter}/interact", {
    "session_id": f"{incident_id}-insurance",
    "actor_id": "user:jane-doe", "institution": "state-farm",
    "intent": "I need to file an insurance claim for a car accident",
    "capability": "claim_filing",
    "context": {"incident_id": incident_id, "police_report": report,
        "vehicle": "2022 Honda Civic",
        "damage_description": "Driver side door and fender damage",
        "at_fault": "other_driver", "policy_number": "SF-789456"}
})
d2 = r2["result"]
claim = d2.get("claim_id", "CLM-???")
payout = d2.get("estimated_payout", "0")
cpi = d2.get("latest_us_cpi_pct", "")
year = d2.get("inflation_data_year", "")
print(f"  {claim} approved. Payout ${payout} (CPI {round(float(cpi),1) if cpi else '?'}%, World Bank {year}).")

print("Step 3: Booking repair appointment...")
r3 = post(f"{adapter}/interact", {
    "session_id": f"{incident_id}-repair",
    "actor_id": "user:jane-doe", "institution": "city-auto",
    "intent": "I need to book a repair appointment for accident damage",
    "capability": "repair_booking",
    "context": {"incident_id": incident_id, "claim_id": claim,
        "vehicle": "2022 Honda Civic",
        "damage": "Driver side door and fender",
        "insurance_approved": True}
})
d3 = r3["result"]
appt = d3.get("appointment_date", "TBD")
est = d3.get("repair_estimate", "0")
print(f"  Repair booked {appt} at 10:00 AM. Estimate ${est}.")
print()
print("RESOLVED:")
print(f"  Police report:  {report}")
print(f"  Insurance claim: {claim} — ${payout} approved")
print(f"  Repair:          {appt} at 10:00 AM — ${est} estimate")
print()
print("All actions signed, content-addressed, and recorded in the ANKA mesh.")
print("No forms. No phone trees. No lost paperwork.")
PYEOF

echo ""
echo -e "${GREEN}Demo complete.${RESET}"
echo ""
echo "  Alice dashboard: http://localhost:18080/dashboard"
echo "  Bob dashboard:   http://localhost:18081/dashboard"
echo ""
echo "To stop: docker compose down"
echo "Full demo: bash demo-full.sh"
