import json, urllib.request, time, sys

def post(url, data):
    try:
        req = urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}

print("=== Publishing to Oxford ===")
pub = post("http://localhost:18080/publish", {
    "claim_space": "research.result.claims",
    "subject": "phase2-convergence-test",
    "predicate": "reported_finding",
    "object": "5-node mesh converged",
    "evidence_refs": [],
    "timestamp_unix_secs": 1775740000
})
if not pub.get("ok"):
    print("FAILED:", pub); sys.exit(1)
digest = pub["digest_hex"]
print(f"Published: {digest[:40]}...")

print("\n=== Fetching to all peers ===")
for port in [18081, 18082, 18083, 18084]:
    r = post(f"http://localhost:{port}/fetch", {
        "digest_hex": digest,
        "sender_address": "http://localhost:18080",
        "timestamp_unix_secs": 1775740010
    })
    print(f"  Port {port}: witnessed={r.get('witnessed', r.get('ok'))}")

time.sleep(2)

print("\n=== Convergence Check ===")
all_ok = True
for port in [18080, 18081, 18082, 18083, 18084]:
    s = get(f"http://localhost:{port}/sync")
    claims = s.get("claim_count", 0)
    witnesses = s.get("witness_count", 0)
    print(f"  Port {port}: claims={claims} witnesses={witnesses}")
    if claims < 1:
        all_ok = False

print()
print("PHASE 2.1 COMPLETE: five-node mesh converged" if all_ok else "PHASE 2.1 INCOMPLETE")
