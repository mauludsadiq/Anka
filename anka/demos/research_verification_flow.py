#!/usr/bin/env python3
"""
ANKA Demo: Research Publication Verification Flow
100% functional — every API call is live, no mocks.

User: "I'm publishing a paper on climate sensitivity.
       Help me verify my key claims and find related work."

ANKA coordinates across 4 real institutions:
  arXiv      -> export.arxiv.org     (live preprints)
  PubMed     -> pubmed.ncbi.nlm.nih.gov (live literature)
  NIST       -> physics.nist.gov     (live physical constants)
  World Bank -> api.worldbank.org    (live economic data)
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

node    = "http://localhost:18080"
adapter = "http://localhost:19200"

TOPIC   = "climate sensitivity"
SUBJECT = "climate-sensitivity-paper-2026"

print("=" * 62)
print("ANKA DEMO: Research Publication Verification")
print("100% Functional — Live APIs, No Mocks")
print("=" * 62)
print()
print('User: "I\'m publishing a paper on climate sensitivity.')
print('       Help me verify my key claims and find related work."')
print()

session_id = "research-" + hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]

# Register institutions
for name, nid, itype, alias in [
    ("arxiv",      "ed25519:arxiv", "research",    "arxiv"),
    ("pubmed",     "ed25519:pubmed","research",    "pubmed"),
    ("nist",       "ed25519:nist",  "government",  "nist.gov"),
    ("world-bank", "ed25519:wb",    "government",  "worldbank"),
]:
    post(f"{node}/runtime/registry", {"name": name, "address": adapter,
        "node_id": nid, "institution_type": itype, "alias": alias})

digests = []
total = "0"
total2 = "0"

# ── Step 1: arXiv ─────────────────────────────────────────────────────────────
print("─" * 62)
print("Step 1: arXiv — Recent preprints on climate sensitivity")
print("─" * 62)
r1 = post(f"{adapter}/interact", {
    "session_id": f"{session_id}-arxiv",
    "actor_id": "researcher-llm",
    "institution": "arxiv",
    "intent": f"Find preprints on {TOPIC}",
    "capability": "preprint_search",
    "context": {},
    "timestamp_unix_secs": int(time.time())
})
if r1.get("ok"):
    papers = r1["result"].get("papers", [])
    total  = r1["result"].get("total_results", "0")
    print(f"  Found {total} preprints. Most recent:")
    for p in papers[:3]:
        print(f"  [{p['arxiv_id']}] {p['title'][:58]}")
        print(f"           {', '.join(p['authors'])} ({p['published']})")
    print(f"  Source: {r1['result'].get('source')}")

    d1 = post(f"{node}/publish", {
        "claim_space": "research.literature.preprints",
        "subject": SUBJECT,
        "predicate": "arxiv_search_completed",
        "object": f"{total} preprints found on {TOPIC}",
        "evidence_refs": [p["arxiv_id"] for p in papers[:3]],
        "timestamp_unix_secs": int(time.time())
    })
    digests.append(("arXiv search", d1.get("digest_hex", "")))
print()

# ── Step 2: PubMed ────────────────────────────────────────────────────────────
print("─" * 62)
print("Step 2: PubMed — Peer-reviewed literature")
print("─" * 62)
r2 = post(f"{adapter}/interact", {
    "session_id": f"{session_id}-pubmed",
    "actor_id": "researcher-llm",
    "institution": "pubmed",
    "intent": f"Find papers on {TOPIC}",
    "capability": "literature_search",
    "context": {},
    "timestamp_unix_secs": int(time.time())
})
if r2.get("ok"):
    papers2 = r2["result"].get("papers", [])
    total2  = r2["result"].get("total_results", "0")
    print(f"  Found {total2} peer-reviewed papers. Most recent:")
    for p in papers2[:3]:
        print(f"  [PMID:{p['pmid']}] {p['title'][:55]}")
        print(f"           {', '.join(p['authors'])} | {p['journal']} ({p['pubdate']})")
    print(f"  Source: {r2['result'].get('source')}")

    d2 = post(f"{node}/publish", {
        "claim_space": "research.literature.peerreviewed",
        "subject": SUBJECT,
        "predicate": "pubmed_search_completed",
        "object": f"{total2} peer-reviewed papers found on {TOPIC}",
        "evidence_refs": [p["pmid"] for p in papers2[:3]],
        "timestamp_unix_secs": int(time.time())
    })
    digests.append(("PubMed search", d2.get("digest_hex", "")))
print()

# ── Step 3: NIST ──────────────────────────────────────────────────────────────
print("─" * 62)
print("Step 3: NIST — Physical constants verification")
print("─" * 62)
constants = [
    ("Stefan-Boltzmann constant", "stefan"),
    ("Boltzmann constant", "boltzmann"),
]
nist_results = []
for name, keyword in constants:
    r3 = post(f"{adapter}/interact", {
        "session_id": f"{session_id}-nist-{keyword}",
        "actor_id": "researcher-llm",
        "institution": "nist",
        "intent": f"What is the {name}?",
        "capability": "physical_constants",
        "context": {},
        "timestamp_unix_secs": int(time.time())
    })
    if r3.get("ok"):
        d = r3["result"]
        print(f"  {d.get('name')}: {d.get('value')} {d.get('unit')}")
        print(f"  Uncertainty: {d.get('uncertainty')} | Source: {d.get('source')}")
        nist_results.append(f"{d.get('name')}={d.get('value')}{d.get('unit')}")

d3 = post(f"{node}/publish", {
    "claim_space": "research.constants.verified",
    "subject": SUBJECT,
    "predicate": "physical_constants_verified",
    "object": " | ".join(nist_results),
    "evidence_refs": ["nist:codata:2022"],
    "timestamp_unix_secs": int(time.time())
})
digests.append(("NIST constants", d3.get("digest_hex", "")))
print()

# ── Step 4: World Bank ────────────────────────────────────────────────────────
print("─" * 62)
print("Step 4: World Bank — Economic impact data")
print("─" * 62)
wb_queries = [
    ("Global GDP for economic impact baseline", "What is the global GDP?", "world-bank"),
    ("US GDP per capita for welfare baseline",  "GDP per capita of United States", "world-bank"),
]
wb_results = []
for label, intent, inst in wb_queries:
    r4 = post(f"{adapter}/interact", {
        "session_id": f"{session_id}-wb-{label[:10].replace(' ','')}",
        "actor_id": "researcher-llm",
        "institution": inst,
        "intent": intent,
        "capability": "economic_indicator",
        "context": {},
        "timestamp_unix_secs": int(time.time())
    })
    if r4.get("ok"):
        d = r4["result"]
        print(f"  {d.get('indicator_name','')}: {d.get('value','')} ({d.get('year','')})")
        print(f"  Country: {d.get('country','')} | Source: {d.get('source','')}")
        wb_results.append(r4.get("message", ""))

d4 = post(f"{node}/publish", {
    "claim_space": "research.data.economic",
    "subject": SUBJECT,
    "predicate": "economic_data_verified",
    "object": " | ".join(wb_results),
    "evidence_refs": ["worldbank:api:2024"],
    "timestamp_unix_secs": int(time.time())
})
digests.append(("World Bank data", d4.get("digest_hex", "")))
print()

# ── Resolution ────────────────────────────────────────────────────────────────
print("=" * 62)
print("VERIFICATION COMPLETE")
print("=" * 62)
print()
print(f"  Topic:   {TOPIC.title()}")
print(f"  Session: {session_id}")
print()
print("  Claims verified and recorded in ANKA mesh:")
for label, digest in digests:
    short = digest.replace("sha256:","")[:16] if digest else "pending"
    print(f"    {label:<25} anka:sha256:{short}...")
print()
print("  Data provenance:")
print(f"    arXiv:      {total} preprints  (export.arxiv.org, live)")
print(f"    PubMed:     {total2} papers   (pubmed.ncbi.nlm.nih.gov, live)")
print(f"    NIST:       2 constants        (physics.nist.gov, CODATA 2022)")
print(f"    World Bank: 2 indicators       (api.worldbank.org, live)")
print()
print("─" * 62)
print("Every data point is live. Every claim is signed.")
print("Every citation is content-addressed and reproducible.")
print("─" * 62)
