# ANKA

**The interoperability substrate for AI-operated systems.**

![Tests](https://img.shields.io/badge/tests-184%20passing-brightgreen)
![Lines](https://img.shields.io/badge/lines-3%2C509-blue)
![Language](https://img.shields.io/badge/language-Fard-purple)
![Status](https://img.shields.io/badge/status-active-success)

Written in [Fard](https://github.com/mauludsadiq/FARD).

-----

## The Claim

The 1990s needed a web. Every institution needed a site, every business needed presence, every system needed to be reachable. HTTP, DNS, and TLS made that possible — not by solving any single problem, but by providing the interoperability primitives that everything else could build on.

The 2030s need the same thing one layer up. AI systems are proliferating across institutions, disciplines, and organizations. They produce high-stakes outputs — research findings, medical recommendations, financial forecasts, legal analysis — and pass them between each other with no infrastructure for provenance, verification, or contestation.

ANKA is the substrate for that layer. Not a model. Not a platform. Not a chatbot. The interoperability primitives that AI-operated systems need to coordinate at scale without a trusted intermediary.

-----

## The Problem

When an AI system at Oxford produces a GDP forecast and passes it to an AI system at the Bank of England, what guarantees does the receiver have? Who signed it? Has anyone independently verified it? Has it been contested? Can the reasoning be replicated?

Today: none. The output is a string. Its provenance is wherever you stored it. Its verification history is whatever you logged. Its contestation record does not exist.

This is not a model problem. Models are getting better. It is an infrastructure problem. The internet has no native primitive for a verifiable claim — a statement that carries its own origin, verification history, and contestation record intrinsically, not as metadata attached elsewhere.

ANKA is that primitive.

-----

## The Web Stack Analogy

The web became the web because a small set of composable primitives made interoperability the default. ANKA is the same bet, one layer up.

|Web     |ANKA                                                                                |
|--------|------------------------------------------------------------------------------------|
|URL     |Content-addressed digest — the digest is not a pointer to the thing, it is the thing|
|DNS     |Claim space registry — namespace resolution with versioned, chained entries         |
|HTTP    |Gossip and fetch pipeline — digest announcement, selective fetch, tamper rejection  |
|TLS     |Ed25519 signatures — cross-node verification without shared secrets                 |
|Sessions|Persistent node identity — SQLite-backed state survives restarts                    |
|APIs    |Executable claims — signed computation with independent recomputation path          |
|Caching |Scoped gossip — bandwidth proportional to subscription, not mesh size               |
|CDN     |Replication layer — signed receipts, durability status queryable per digest         |
|Search  |Query and collapse API — policy-collapsed answer with provenance in one call        |
|Auth    |Identity binding — institutional declarations countersigned by origin               |

These are not features. They are web primitives — the minimum set required for AI systems to coordinate without a trusted intermediary.

-----

## What Is Built

**Substrate layer — complete and tested.**

164 tests passing across 27 test files. 3,500 lines of Fard. The following properties are verified in live multi-process tests, not simulations:

**5-node full mesh convergence.** One published claim propagates automatically to all five nodes via gossip, fetch, verify, and witness. 5/5 nodes converge. 4/5 issue structural witnesses. No manual intervention. No central coordinator.

**Scoped gossip at scale.** Econ-subscribed nodes receive zero science claims. Science-subscribed nodes receive zero econ claims. Wildcard nodes receive both. Bandwidth is proportional to subscription, not mesh size. This is not an optimization — at agent scale it is a requirement.

**Ed25519 across the full protocol.** Every claim, witness, challenge, role declaration, collapse result, and replication receipt is signed with an asymmetric key. A node at Oxford verifies a claim from MIT without any shared secret — only the signer’s public key, derivable from their declared node identity.

**Automatic audit trail.** Every publish, witness, and challenge is automatically appended to the claim trail. Queryable by digest. Full epistemic history survives the session, the process restart, and the node operator.

**Policy-collapsed answers with provenance.** `GET /query/{claim_space}/{subject}` returns the winner, scores, and full provenance of all competing claims in a single call. The consumer decides whether to trust the answer based on the witness history, not on the node’s word.

**Registry bootstrap.** A node joining cold fetches the genesis registry from the origin and discovers all registered claim spaces via chain-verified sync. No manual configuration.

**Institutional identity binding.** Nodes declare signed identity objects binding their Ed25519 key to institution, department, and role. Verifiable by any peer. Optionally countersigned by the origin node.

**Rate limiting.** Sliding window counters per endpoint. 429 on excess. Configurable per deployment.

**SDK.** `sdk.fard` exposes the full node API as importable functions. Any Fard program can interact with an ANKA mesh in three lines.

**Dashboard.** `GET /dashboard` on any node serves a live operator UI — claims, witnesses, digests, peers, registry, and audit trail. No build chain, no npm, no separate process. Ships with every node.

**Agent adapter.** `agent.fard` provides `publish_llm_output`, `verified_query`, and `cite` — the three operations an AI system needs to participate in the mesh. Publish an output as a verifiable claim. Query with a minimum witness threshold. Fetch a claim by digest and get its full provenance.

-----

## What This Enables

**Verifiable AI outputs.** Any AI system can publish its output as a signed claim and receive a digest — a stable, verifiable identity for that output that any other system can check.

```
let result = agent.publish_llm_output(client, "econ.space", "GDP_Q3",
  "forecast", llm_output, ["model:gpt-4o", "data:labor_v1"])
result.cite_as  =>  "anka:sha256:..."
```

**Cited sources with intrinsic provenance.** A RAG system that cites `anka:sha256:...` instead of a URL is citing something that cannot change, cannot be taken down, and whose verification history is queryable by anyone.

**Cross-institutional claim coordination.** Two research groups at different institutions publish competing findings. Both survive in the mesh with their full evidence and witness histories. A consuming system applies its own declared policy to decide what to act on. No central arbiter.

**Executable claims with independent verification.** A node publishes a computation — not just its result, but the expression, input refs, and output. Any validator node recomputes independently. A mismatch produces a signed challenge that any other node can verify.

-----

## The Primitive

```
identity = H(canonical object)
```

Every object in ANKA has an identity that is its content. H is SHA-256 over the canonical JSON serialization. The digest is not a pointer — it is the thing. Two objects with the same digest are the same object. Tamper with the content and you produce a new digest that does not match what peers have witnessed.

This gives the network three properties HTTP cannot provide:

1. **Stable identity.** A digest refers to exactly one object, across all nodes, across all time.
1. **Intrinsic provenance.** Signatures, witnesses, challenges, and reconstruction paths are part of the object.
1. **Tamper evidence without a central authority.** Any node can verify any object against its digest without asking permission.

-----

## Claim Spaces

The most important design decision in ANKA is the formal distinction between two kinds of epistemic domain.

**Invariant spaces** admit objective canonicalization. Cryptographic proofs, compiler outputs, deterministic execution traces. Two honest nodes running the same verification always reach the same conclusion.

**Interpretive spaces** admit only policy-relative canonicalization. Economic forecasts, medical findings, legal interpretation, scientific consensus in contested domains. No global canonical truth exists. Competing claims coexist indefinitely. The claim set is not a problem to be resolved — it is a faithful representation of genuine epistemic disagreement.

A Resolution object type was considered and rejected. Collapse happens at the policy layer per consuming node. The substrate preserves divergence. What to act on is a local decision under declared rules.

-----

## Quickstart

**Option 1: Docker (recommended)**

```bash
git clone https://github.com/mauludsadiq/Anka && cd Anka
docker-compose up
```

Starts origin, two mesh nodes, and a policy node. No Fard runtime required.

**Option 2: Local (requires [Fard](https://github.com/mauludsadiq/FARD) runtime)**

```bash
git clone https://github.com/mauludsadiq/Anka && cd Anka

# Start origin and a mesh node
fardrun run --program anka/src/origin_process.fard --out out/origin &
fardrun run --program anka/src/node_process.fard --out out/node &
sleep 2

# Bootstrap registry from origin
curl -X POST http://localhost:18080/registry/fetch \
  -H "Content-Type: application/json" \
  -d '{"sender_address":"http://localhost:18090"}'

# Publish a claim
curl -X POST http://localhost:18080/publish \
  -H "Content-Type: application/json" \
  -d '{
    "claim_space": "anka.interpretive.econ",
    "subject": "GDP_Q3_2026",
    "predicate": "forecast_growth",
    "object": "2.3",
    "evidence_refs": ["labor_data:v1"],
    "timestamp_unix_secs": 1775710900
  }'

# Query with collapse and provenance
curl http://localhost:18080/query/anka.interpretive.econ/GDP_Q3_2026
```

Or via the Fard SDK:

```
import("sdk") as sdk
import("agent") as agent

let c = sdk.client("http://localhost:18080")
let result = agent.publish_llm_output(c, "anka.interpretive.econ",
  "GDP_Q3_2026", "forecast_growth", "2.3", ["labor_data:v1"])
result.cite_as
```

-----

## Node API

**Claims**

```
POST /publish                          Publish a signed claim
GET  /claim/{digest}                   Fetch a claim envelope by digest
GET  /query/{claim_space}/{subject}    Collapsed answer with full provenance
POST /gossip                           Receive a gossip digest from a peer
POST /fetch                            Fetch, verify, and witness a claim
```

**Witnessing and Challenges**

```
POST /witness                          Record a witness attestation
POST /challenge                        Record a challenge
```

**Peers and Subscriptions**

```
POST /peer                             Register a peer
GET  /peers                            List peers
POST /subscribe                        Set subscription spaces
GET  /subscriptions                    List subscriptions
```

**Registry**

```
GET  /registry                         Local registry snapshot
POST /registry/fetch                   Fetch and apply registry from a peer
```

**Audit**

```
GET  /audit                            Archive summary
GET  /audit/trail/{digest}             Full epistemic trail for a claim
GET  /sync                             Node state summary
GET  /health                           Node health and identity
```

-----

## Running the Tests

```bash
# Unit and protocol tests (no live node required)
fardrun test --program anka/tests/test_anka_layer1.fard
fardrun test --program anka/tests/test_keypair.fard
fardrun test --program anka/tests/test_identity.fard

# Integration tests (requires live node)
fardrun run --program anka/src/node_process.fard --out out/node &
sleep 2
fardrun test --program anka/tests/test_sdk_integration.fard
fardrun test --program anka/tests/test_agent.fard
```

See `DEPLOYMENT.md` for TLS configuration, key management, and multi-institutional setup.

-----

## What Is Not Built Yet

The substrate is complete. The application layer is not.

**Discovery registry.** Nodes find each other by address. There is no mechanism for an Oxford node to discover a MIT node without prior out-of-band coordination. A signed registry of institutional nodes closes this gap. In progress.

**Economic security layer.** In a permissioned institutional mesh, Ed25519 identity declarations provide sufficient Sybil resistance. For open participation, staking and slashing are needed. The reputation model is the foundation; token economics would sit on top of it.

**First production deployment.** The protocol is ready. The mesh has been tested. What remains is running it between two institutions on separate machines with real operators and real claims.

# License

MUI 