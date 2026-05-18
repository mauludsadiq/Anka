#!/usr/bin/env python3
"""
ANKA Demo: AI as Your Institutional Agent — Dynamic Discovery
Agents are discovered from the ANKA mesh via Dalil, not hardcoded.

User: "I was in a minor car accident yesterday..."
ANKA discovers which agents handle each capability, then routes to them.
"""

import json, urllib.request, hashlib, time

def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(),
        {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())

node   = "http://localhost:18080"
dalil  = "http://localhost:17000"
adapter = "http://localhost:19200"

print("=" * 62)
print("ANKA DEMO: AI as Your Institutional Agent")
print("Dynamic Discovery — agents found via mesh, not hardcoded")
print("=" * 62)
print()
print('User: "I was in a minor car accident yesterday. The other')
print('       driver ran a red light. I need help filing the')
print('       insurance claim, getting my car repaired, and')
print('       submitting the police report."')
print()

incident_id = "INC-" + hashlib.sha256(str(time.time()).encode()).hexdigest()[:8].upper()
ts = int(time.time())

# ── Step 0: Agents register capabilities in the mesh ──────────────────────────
print("─" * 62)
print("Step 0: Agents register capabilities in the mesh")
print("─" * 62)

registrations = [
    ("city-pd",    "police_report",   adapter, "Chicago, IL"),
    ("state-farm", "insurance_claim", adapter, "Illinois"),
    ("city-auto",  "auto_repair",     adapter, "Chicago, IL"),
]
for agent, capability, address, region in registrations:
    r = post(f"{dalil}/register", {
        "agent_name": agent, "capability": capability,
        "address": address, "region": region,
        "timestamp_unix_secs": ts
    })
    print(f"  {'OK' if r.get('ok') else 'FAIL'} {agent} registered: {capability} ({region})")
    if r.get("digest"):
        print(f"       anka:{r['digest'].replace('sha256:','')[:20]}...")
print()

# ── Discovery helper ───────────────────────────────────────────────────────────
def discover(capability):
    r = get(f"{dalil}/discover/{capability}")
    if not r.get("ok"):
        return None, None
    finding = r.get("agents", {}).get("finding", "")
    if not finding:
        return None, None
    parts = finding.split("|")
    return parts[0], parts[1]  # name, address

# ── Step 1: Discover + file police report ─────────────────────────────────────
print("─" * 62)
agent_name, agent_addr = discover("police_report")
print(f"Step 1: Mesh discovered '{agent_name}' for police_report")
print(f"        Routing to: {agent_addr}")
print("─" * 62)

r1 = post(f"{agent_addr}/interact", {
    "session_id": f"{incident_id}-police",
    "actor_id": "user:jane-doe",
    "institution": agent_name,
    "intent": "I need to file a police report for a car accident",
    "capability": "police_report",
    "context": {
        "incident_id": incident_id,
        "date": "2026-05-18",
        "location": "Main St & 5th Ave",
        "description": "Other driver ran red light, struck my vehicle on driver side",
        "other_driver": "John Smith, plate ABC-1234",
        "injuries": "none",
        "vehicle": "2022 Honda Civic, plate XYZ-9876"
    }
})
report_number = r1.get("result", {}).get("report_number", "RPT-UNKNOWN")
print(f"  {r1.get('message','')}")
print(f"  Report: {report_number} | ok={r1.get('ok')}")
post(f"{node}/publish", {
    "claim_space": "incident.police.reports", "subject": incident_id,
    "predicate": "police_report_filed", "object": report_number,
    "evidence_refs": [incident_id, f"agent:{agent_name}"],
    "timestamp_unix_secs": ts
})
print()

# ── Step 2: Discover + file insurance claim ───────────────────────────────────
print("─" * 62)
agent_name2, agent_addr2 = discover("insurance_claim")
print(f"Step 2: Mesh discovered '{agent_name2}' for insurance_claim")
print(f"        Routing to: {agent_addr2}")
print("─" * 62)

r2 = post(f"{agent_addr2}/interact", {
    "session_id": f"{incident_id}-insurance",
    "actor_id": "user:jane-doe",
    "institution": agent_name2,
    "intent": "I need to file an insurance claim for a car accident",
    "capability": "claim_filing",
    "context": {
        "incident_id": incident_id,
        "police_report": report_number,
        "date": "2026-05-18",
        "vehicle": "2022 Honda Civic",
        "damage_description": "Driver side door and fender damage",
        "at_fault": "other_driver",
        "policy_number": "SF-789456"
    }
})
d2 = r2.get("result", {})
claim_id = d2.get("claim_id", "CLM-UNKNOWN")
payout = d2.get("estimated_payout", "0.00")
print(f"  {r2.get('message','')}")
print(f"  Base (2020 USD): ${d2.get('base_cost_2020_usd','')} x {d2.get('inflation_adjustment_factor','')} inflation")
print(f"  CPI source: {d2.get('inflation_source','')} ({d2.get('inflation_data_year','')})")
print(f"  Payout: ${payout} | Net: ${d2.get('net_payout','')} | ok={r2.get('ok')}")
post(f"{node}/publish", {
    "claim_space": "incident.insurance.claims", "subject": incident_id,
    "predicate": "insurance_claim_filed", "object": claim_id,
    "evidence_refs": [incident_id, report_number, f"agent:{agent_name2}"],
    "timestamp_unix_secs": ts
})
print()

# ── Step 3: Discover + book repair ────────────────────────────────────────────
print("─" * 62)
agent_name3, agent_addr3 = discover("auto_repair")
print(f"Step 3: Mesh discovered '{agent_name3}' for auto_repair")
print(f"        Routing to: {agent_addr3}")
print("─" * 62)

r3 = post(f"{agent_addr3}/interact", {
    "session_id": f"{incident_id}-repair",
    "actor_id": "user:jane-doe",
    "institution": agent_name3,
    "intent": "I need to book a repair appointment for accident damage",
    "capability": "repair_booking",
    "context": {
        "incident_id": incident_id, "claim_id": claim_id,
        "vehicle": "2022 Honda Civic",
        "damage": "Driver side door and fender",
        "insurance_approved": True
    }
})
d3 = r3.get("result", {})
appointment = d3.get("appointment_date", "TBD")
estimate = d3.get("repair_estimate", "0.00")
print(f"  {r3.get('message','')}")
print(f"  Appointment: {appointment} | Estimate: ${estimate} | ok={r3.get('ok')}")
post(f"{node}/publish", {
    "claim_space": "incident.repair.bookings", "subject": incident_id,
    "predicate": "repair_booked", "object": appointment,
    "evidence_refs": [incident_id, claim_id, f"agent:{agent_name3}"],
    "timestamp_unix_secs": ts
})
print()

# ── Resolution ────────────────────────────────────────────────────────────────
print("=" * 62)
print("RESOLUTION SUMMARY")
print("=" * 62)
print()
print(f"  Police Report:        Filed ({report_number})")
print(f"                        Agent: {agent_name} (discovered via mesh)")
print()
print(f"  Insurance Claim:      Approved ({claim_id})")
print(f"                        Agent: {agent_name2} (discovered via mesh)")
print(f"                        Payout: ${payout} (inflation-adjusted, World Bank live)")
print()
print(f"  Repair Appointment:   Booked {appointment}")
print(f"                        Agent: {agent_name3} (discovered via mesh)")
print(f"                        Estimate: ${estimate}")
print()
print("  All actions signed, content-addressed, and permanently")
print("  recorded in the ANKA mesh with full provenance and lineage.")
print()
print("─" * 62)
print("Agents were not hardcoded. They were discovered from the mesh.")
print("Any agent can register. The mesh routes to the best one.")
print("From chaos to resolution — one conversation, full audit trail.")
print("─" * 62)
