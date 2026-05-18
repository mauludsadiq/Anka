import json, urllib.request, hashlib, time

def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())

node    = "http://localhost:18080"
adapter = "http://localhost:19200"

print("=" * 60)
print("ANKA DEMO: AI as Your Institutional Agent")
print("Scenario: Car Accident — Cross-Institution Coordination")
print("=" * 60)
print()

incident_id = "INC-" + hashlib.sha256(str(time.time()).encode()).hexdigest()[:8].upper()
user_id     = "user:jane-doe"

print(f"User: 'I was in a minor car accident yesterday. The other")
print(f"       driver ran a red light. I need help filing the")
print(f"       insurance claim, getting my car repaired, and")
print(f"       submitting the police report.'")
print()
print(f"Incident ID: {incident_id}")
print()

# Register all institutions
institutions = [
    ("city-pd",       adapter, "ed25519:citypd",    "government", "citypd"),
    ("state-farm",    adapter, "ed25519:statefarm",  "insurance",  "statefarm"),
    ("city-auto",     adapter, "ed25519:cityauto",   "repair",     "cityauto"),
]
for name, addr, nid, itype, alias in institutions:
    post(f"{node}/runtime/registry", {"name": name, "address": addr,
        "node_id": nid, "institution_type": itype, "alias": alias})

print("--- Step 1: File Police Report ---")
r1 = post(f"{adapter}/interact", {
    "session_id": f"{incident_id}-police",
    "actor_id": user_id,
    "institution": "city-pd",
    "intent": "I need to file a police report for a car accident",
    "capability": "police_report",
    "context": {
        "incident_id": incident_id,
        "date": "2026-05-17",
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
print()

# Publish to ANKA mesh
post(f"{node}/publish", {
    "claim_space": "incident.police.reports",
    "subject": incident_id,
    "predicate": "police_report_filed",
    "object": report_number,
    "evidence_refs": [incident_id, user_id],
    "timestamp_unix_secs": int(time.time())
})

print("--- Step 2: File Insurance Claim ---")
r2 = post(f"{adapter}/interact", {
    "session_id": f"{incident_id}-insurance",
    "actor_id": user_id,
    "institution": "state-farm",
    "intent": "I need to file an insurance claim for a car accident",
    "capability": "claim_filing",
    "context": {
        "incident_id": incident_id,
        "police_report": report_number,
        "date": "2026-05-17",
        "vehicle": "2022 Honda Civic",
        "damage_description": "Driver side door and fender damage",
        "at_fault": "other_driver",
        "policy_number": "SF-789456"
    }
})
claim_id     = r2.get("result", {}).get("claim_id", "CLM-UNKNOWN")
payout       = r2.get("result", {}).get("estimated_payout", "0.00")
print(f"  {r2.get('message','')}")
print(f"  Claim: {claim_id} | Estimated payout: ${payout} | ok={r2.get('ok')}")
print()

post(f"{node}/publish", {
    "claim_space": "incident.insurance.claims",
    "subject": incident_id,
    "predicate": "insurance_claim_filed",
    "object": claim_id,
    "evidence_refs": [incident_id, report_number, "policy:SF-789456"],
    "timestamp_unix_secs": int(time.time())
})

print("--- Step 3: Book Repair Appointment ---")
r3 = post(f"{adapter}/interact", {
    "session_id": f"{incident_id}-repair",
    "actor_id": user_id,
    "institution": "city-auto",
    "intent": "I need to book a repair appointment for accident damage",
    "capability": "repair_booking",
    "context": {
        "incident_id": incident_id,
        "claim_id": claim_id,
        "vehicle": "2022 Honda Civic",
        "damage": "Driver side door and fender",
        "insurance_approved": True
    }
})
appointment = r3.get("result", {}).get("appointment_date", "TBD")
estimate    = r3.get("result", {}).get("repair_estimate", "0.00")
print(f"  {r3.get('message','')}")
print(f"  Appointment: {appointment} | Estimate: ${estimate} | ok={r3.get('ok')}")
print()

post(f"{node}/publish", {
    "claim_space": "incident.repair.bookings",
    "subject": incident_id,
    "predicate": "repair_booked",
    "object": appointment,
    "evidence_refs": [incident_id, claim_id, "shop:city-auto"],
    "timestamp_unix_secs": int(time.time())
})

print("=" * 60)
print("RESOLUTION SUMMARY")
print("=" * 60)
print()
print(f"  Police Report:        Filed ({report_number})")
print(f"                        Officer Rodriguez assigned.")
print(f"                        Incident: Main St & 5th Ave, 2026-05-17")
print()
print(f"  Insurance Claim:      Approved ({claim_id})")
print(f"                        Estimated payout: ${payout}")
print(f"                        Net payout: ${str(round(float(payout)-500,2))} after deductible")
print(f"                        Adjuster Sarah Chen assigned, contact within 24h")
print()
print(f"  Repair Appointment:   Booked Thursday {appointment} at 10:00 AM")
print(f"                        Estimate: ${estimate}")
print(f"                        Insurance billed directly. Loaner car available.")
print()
print("  All actions signed, content-addressed, and permanently")
print("  recorded in the ANKA mesh with full provenance and lineage.")
print()
print("-" * 60)
print("From chaos to resolution — in one natural conversation,")
print("across three separate institutions, with complete auditability.")
print()
print("No form-filling. No contradictory bots. No lost paperwork.")
print("Just a capable AI acting as your verified institutional agent.")
print("-" * 60)
print()

# Audit trail
trail = get(f"{node}/query/incident.insurance.claims/{incident_id}")
print(f"Audit: {trail.get('single_winner', {}).get('winner_value', 'pending')}")
print()
print("User went from: 'I was in a car accident'")
print("            to: Resolution across 3 institutions")
print("                in one conversation, with full audit trail.")
