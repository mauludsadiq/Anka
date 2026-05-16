# ANKA

**The interoperability substrate for AI-operated systems.**

![Tests](https://img.shields.io/badge/tests-262%20passing-brightgreen)
![Lines](https://img.shields.io/badge/lines-4%2C602-blue)
![Language](https://img.shields.io/badge/language-Fard-purple)
![Status](https://img.shields.io/badge/status-active-success)

Written in [Fard](https://github.com/mauludsadiq/FARD).

-----

## The Claim

The 1990s needed a web. Every institution needed a site, every business needed presence, every system needed to be reachable. HTTP, DNS, and TLS made that possible — not by solving any single problem, but by providing the interoperability primitives that everything else could build on.

The 2030s need the same thing one layer up. AI systems are proliferating across institutions, disciplines, and organizations. They produce high-stakes outputs — research findings, medical recommendations, financial forecasts, legal analysis — and pass them between each other with no infrastructure for provenance, verification, or contestation.

ANKA is the substrate for that layer. Not a model. Not a platform. Not a chatbot. The interoperability primitives that AI-operated systems need to coordinate at scale without a trusted intermediary.

-----

## The Stack

ANKA sits above Bay2 — the operational substrate for AI-operated systems.

    Bay2          <- storage, streaming, capabilities, pubsub, replay, metering
      |
    ANKA          <- claims, witnesses, collapse, audit, reputation, coordination
      |
    AI systems    <- research meshes, scientific coordination, institutional trust

Bay2 handles storage, transport, causal streaming, capabilities, materialized views, replication, policy enforcement, deterministic replay, and economic metering. ANKA handles epistemic coordination — claims, witnesses, challenges, collapse, audit, and institutional identity. Neither knows about the other's internals. A bridge module translates between them.

Bay2 repo: https://github.com/mauludsadiq/Bay2

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

262 tests passing across 35 test files. 4,602 lines of Fard. The following properties are verified in live multi-process tests, not simulations:

**5-node full mesh convergence.** One published claim propagates automatically to all five nodes via gossip, fetch, verify, and witness. 5/5 nodes converge. 4/5 issue structural witnesses. No manual intervention. No central coordinator.

**Scoped gossip at scale.** Econ-subscribed nodes receive zero science claims. Science-subscribed nodes receive zero econ claims. Wildcard nodes receive both. Bandwidth is proportional to subscription, not mesh size.

**Ed25519 across the full protocol.** Every claim, witness, challenge, role declaration, collapse result, and replication receipt is signed with an asymmetric key. A node at Oxford verifies a claim from MIT without any shared secret.

**Automatic audit trail.** Every publish, witness, and challenge automatically appended to the claim trail. Queryable by digest. Full epistemic history survives process restarts.

**Policy-collapsed answers with provenance.** `GET /query/{claim_space}/{subject}` returns the winner, scores, and full provenance of all competing claims in a single call.

**Registry bootstrap with nine canonical claim spaces.** A node joining cold fetches the genesis registry and discovers all registered spaces via chain-verified sync:

|Claim Space                |Type        |Policy       |Purpose                                                       |
|---------------------------|------------|-------------|--------------------------------------------------------------|
|`anka.invariant.crypto`    |invariant   |single-winner|Cryptographic proofs and attestations                         |
|`anka.invariant.compute`   |invariant   |single-winner|Deterministic computation results                             |
|`anka.interpretive.econ`   |interpretive|plural       |Economic forecasts and models                                 |
|`anka.interpretive.science`|interpretive|plural       |Scientific findings and forecasts                             |
|`fard.execution.receipts`  |invariant   |single-winner|Execution receipts and deterministic replay artifacts         |
|`dataset.provenance`       |invariant   |single-winner|Dataset identity, source lineage, content-addressed provenance|
|`model.training.trace`     |invariant   |single-winner|Training traces, checkpoints, optimizer events, run receipts  |
|`research.result.claims`   |interpretive|plural       |Research findings, reported metrics, interpretations          |
|`reproducibility.results`  |invariant   |single-winner|Independent reproduction attempts and verification outcomes   |

**Institutional identity binding.** Nodes declare signed identity objects binding their Ed25519 key to institution, department, and role. Verifiable by any peer. Optionally countersigned by the origin node.

**Discovery registry.** The origin serves `GET /discovery` — a signed registry of institutional nodes. Any node registers via `POST /discovery/register` with a valid Ed25519-signed entry. Any joining node fetches the registry, verifies every entry against its declared public key, and bootstraps peer connections automatically.

**Observer dashboard.** `GET /dashboard` on any node serves a live operator UI — node topology, claim graph tagged by invariant/interpretive, audit feed with timestamped publish/witness/challenge events, peer health status, registry state, convergence tracker, and node identity. Corporate blue/white design. No build chain, no npm, no separate process. Auto-refreshes every 8 seconds.

**Rate limiting.** Sliding window counters per endpoint. 429 on excess. Configurable per deployment.

**SDK.** `sdk.fard` exposes the full node API as importable Fard functions. Any Fard program can interact with an ANKA mesh in three lines.

**Agent adapter.** `agent.fard` provides `publish_llm_output`, `verified_query`, and `cite` — the three operations an AI system needs to participate in the mesh.

**Python verifier.** `anka_sdk/anka/verifier.py` — Python-side verification of executable claims, including runtime digest, stdout digest, and independent recomputation.

**Docker.** `docker-compose up` starts origin, two mesh nodes, and a policy node. No Fard runtime required.

-----

## What This Enables

**Verifiable AI outputs.** Any AI system publishes its output as a signed claim and receives a digest — a stable, verifiable identity for that output that any other system can check.

```
let result = agent.publish_llm_output(client, "research.result.claims", "climate-sensitivity-2026",
  "reported_finding", llm_output, ["ipcc_ar7:draft", "model:gpt-4o"])
result.cite_as  =>  "anka:sha256:..."
```

**Cited sources with intrinsic provenance.** A RAG system that cites `anka:sha256:...` instead of a URL is citing something that cannot change, cannot be taken down, and whose verification history is queryable by anyone.

**Cross-institutional claim coordination.** Two research groups at different institutions publish competing findings. Both survive in the mesh with their full evidence and witness histories. A consuming system applies its own declared policy to decide what to act on. No central arbiter.

**Reproducibility as a first-class primitive.** A result published to `research.result.claims` can be independently replicated and the replication outcome published to `reproducibility.results`. The two claims are linked by subject. Any node can query both and compare.

**Dataset and model provenance.** Training data published to `dataset.provenance`, training runs published to `model.training.trace`. The full lineage of a model — from data to checkpoint — is queryable as a chain of verifiable claims.

-----

## The Primitive

```
identity = H(canonical object)
```

Every object in ANKA has an identity that is its content. H is SHA-256 over the canonical JSON serialization. The digest is not a pointer — it is the thing. Tamper with the content and you produce a new digest that does not match what peers have already witnessed.

This gives the network three properties HTTP cannot provide:

1. **Stable identity.** A digest refers to exactly one object, across all nodes, across all time.
1. **Intrinsic provenance.** Signatures, witnesses, challenges, and reconstruction paths are part of the object.
1. **Tamper evidence without a central authority.** Any node can verify any object against its digest without asking permission.

-----

## Claim Spaces

**Invariant spaces** admit objective canonicalization. Cryptographic proofs, compiler outputs, deterministic execution traces. Two honest nodes running the same verification always reach the same conclusion.

**Interpretive spaces** admit only policy-relative canonicalization. Economic forecasts, medical findings, legal interpretation, scientific consensus in contested domains. Competing claims coexist indefinitely. The claim set is not a problem to be resolved — it is a faithful representation of genuine epistemic disagreement.

Collapse happens at the policy layer per consuming node. The substrate preserves divergence. What to act on is a local decision under declared rules.

-----

## Quickstart

**Try the demo first**

```bash
git clone https://github.com/mauludsadiq/Anka && cd Anka
bash demo.sh
```

Two researchers. One research finding. Independent replication. Verifiable result. ~45 seconds from cold start. No configuration required.

**Option 1: Docker**

```bash
git clone https://github.com/mauludsadiq/Anka && cd Anka
docker-compose up
```

Starts origin, Alice node, Bob node, and policy node. Runs the full Alice/Bob reproducibility demo automatically once nodes are healthy. No Fard runtime required. Persistent SQLite volumes survive restarts.

**Option 2: Local (requires [Fard](https://github.com/mauludsadiq/FARD) runtime)**

```bash
git clone https://github.com/mauludsadiq/Anka && cd Anka

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
    "claim_space": "research.result.claims",
    "subject": "climate-sensitivity-2026",
    "predicate": "reported_finding",
    "object": "3.2C per doubling",
    "evidence_refs": ["ipcc_ar7:draft"],
    "timestamp_unix_secs": 1775710900
  }'

# Query with collapse and provenance
curl http://localhost:18080/query/research.result.claims/climate-sensitivity-2026

# Open the dashboard
open http://localhost:18080/dashboard
```

Or via the Fard SDK:

```
import("sdk") as sdk
import("agent") as agent

let c = sdk.client("http://localhost:18080")
let result = agent.publish_llm_output(c, "research.result.claims",
  "climate-sensitivity-2026", "reported_finding", "3.2C per doubling", ["ipcc_ar7:draft"])
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

**Audit and State**

```
GET  /audit                            Archive summary
GET  /audit/trail/{digest}             Full epistemic trail for a claim
GET  /sync                             Node state summary
GET  /health                           Node health and identity
GET  /dashboard                        Live operator dashboard
```

**Discovery (origin node)**

```
GET  /discovery                        Signed registry of institutional nodes
POST /discovery/register               Register a new institutional node
```

-----

## Running the Tests

```bash
# Protocol tests (no live node required)
fardrun test --program anka/tests/test_anka_layer1.fard
fardrun test --program anka/tests/test_keypair.fard
fardrun test --program anka/tests/test_identity.fard
fardrun test --program anka/tests/test_discovery.fard

# Integration tests (requires live node on port 18080)
fardrun run --program anka/src/node_process.fard --out out/node &
sleep 2
fardrun test --program anka/tests/test_sdk_integration.fard
fardrun test --program anka/tests/test_agent.fard
```

See `DEPLOYMENT.md` for TLS configuration, key management, and multi-institutional setup.

-----

## What Is Not Built Yet

**Bay2 integration.** The ANKA-Bay2 bridge specification is complete and verified with 14 tests. The next step is wiring ANKA's node processes to use Bay2 as the underlying storage and transport layer, replacing the current SQLite-backed flat store with Bay2's sharded object store and causal streams.

**First production deployment.** The protocol is ready. The mesh has been tested across five nodes on one machine. The economic layer is implemented. What remains is running it between two institutions on separate machines, with real operators, real claim spaces, and real stakes.

# License

MUI 