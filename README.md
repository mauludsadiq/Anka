# ANKA

**The interoperability substrate for AI-operated systems.**

Written in [Fard](https://github.com/mauludsadiq/FARD).

![Tests](https://img.shields.io/badge/tests-178%20passing-brightgreen)
![Lines](https://img.shields.io/badge/lines-3%2C401-blue)
![Language](https://img.shields.io/badge/language-Fard-purple)
![Status](https://img.shields.io/badge/status-active-success)

-----

## The Claim

In the 1990s, every company needed a website. By 2030, every company operating AI systems will need those systems connected to each other — not through APIs bolted onto human-facing infrastructure, but through a substrate designed for machine-to-machine coordination from the ground up.

ANKA is that substrate. It is to the AI-native internet what HTTP, DNS, and TLS are to the human web — not an application, not a model, not a platform. The interoperability layer that everything else runs on top of.

-----

## The Problem

AI systems are producing high-stakes claims — research findings, medical recommendations, legal analysis, financial forecasts — with no infrastructure for verifying where those claims came from, who checked them, or whether they were contested.

The current workarounds are bad. RAG systems cite URLs that change. Fine-tuned models inherit training data provenance that nobody can reconstruct. Agents pass outputs between each other with no attestation layer. When something goes wrong, there is no trail.

This is not a model problem. It is an infrastructure problem. The internet has no native primitive for a verifiable claim — a statement with intrinsic provenance, independent verification, and a contestation record that survives the session that produced it.

ANKA is that primitive.

-----

## The Web Stack Analogy

The web became the web because a small set of composable primitives — URLs, HTTP, DNS, TLS — made interoperability the default. No central coordinator. No shared database. Any node that speaks the protocol can participate.

ANKA is the same bet, one layer up.

|Web Primitive|ANKA Equivalent         |What It Does                                                                                   |
|-------------|------------------------|-----------------------------------------------------------------------------------------------|
|URL          |Content-addressed digest|Stable identity across all nodes, all time. The digest is not a pointer — it is the thing.     |
|DNS          |Claim space registry    |Namespace resolution with versioned, chained entries. Bootstrap from genesis.                  |
|HTTP         |Gossip + fetch pipeline |Digest announcement, selective fetch, tamper rejection at transport.                           |
|TLS          |Ed25519 signatures      |Cross-node identity verification without shared secrets.                                       |
|Sessions     |Persistent node identity|SQLite-backed state survives restarts. A node rejoins the mesh with full prior state.          |
|APIs         |Executable claims       |Signed computation with input refs, result, and independent recomputation path.                |
|Caching      |Scoped gossip           |Nodes receive only subscribed claim spaces. Bandwidth proportional to interest, not node count.|
|CDN          |Replication layer       |Declared archive nodes with signed receipts. Durability status queryable per digest.           |
|Search       |Query and collapse API  |Policy-collapsed answer with provenance in a single call.                                      |
|Auth         |Identity binding        |Institutional declarations binding Ed25519 keys to institution, department, role.              |
|Rate limiting|Sliding window counters |Per-endpoint, per-node. 429 on excess.                                                         |
|Audit log    |Claim trail             |Every publish, witness, and challenge automatically appended. Queryable by digest.             |

These are not features. They are web primitives — the minimum set required for AI systems to coordinate at scale without a trusted intermediary.

-----

## What ANKA Is Not

- Not a model. ANKA does not run inference.
- Not a platform. ANKA does not host agents.
- Not a blockchain. ANKA does not require global consensus. Divergence in interpretive domains is preserved, not resolved.
- Not a database. ANKA does not require a trusted operator. Any node can verify any claim against its digest without asking permission.
- Not a RAG system. ANKA does not retrieve documents. It routes verifiable claims with intrinsic provenance.

-----

## The Primitive

```
identity = H(canonical object)
```

Every object in ANKA has an identity that is its content. The digest is not a pointer — it is the thing. Two objects with the same digest are the same object. An object with a different digest is a different object. There is no indirection, no mutable reference, no update-in-place.

**H** is SHA-256 over the canonical JSON serialization of the object. The hash function is declared in the genesis registry and is not extensible at runtime. A claim space that uses a different hash function is a different claim space, not a version of this one. Identity is not parameterized.

This gives the network three properties that HTTP cannot provide:

1. **Stable identity.** A digest always refers to exactly one object, across all nodes, across all time.
1. **Intrinsic provenance.** Every object carries its own epistemic trail. Signatures, witnesses, challenges, and reconstruction paths are part of the object, not metadata attached elsewhere.
1. **Tamper evidence without a central authority.** Any node can verify any object against its digest without asking anyone’s permission.

-----

## Architecture

ANKA is an epistemic routing layer. The network object is not content — it is verifiable claim state.

### Claims

A claim is a signed statement: a subject, a predicate, an object, a set of evidence references, an issuer identity, and a timestamp. The claim is canonically serialized and hashed to produce its digest. The issuer signs the digest with their Ed25519 private key. The envelope — claim plus digest plus signature — is the atomic unit of the network.

```
ClaimEnvelope:  claim_space / subject / predicate / object / evidence_refs / issuer_node_id / timestamp / digest / signature
```

### Gossip

Nodes gossip digests, not payloads. When a node publishes a claim, it announces the digest to peers. Peers fetch the full envelope only if the claim falls within their declared subscription. At agent scale, no node should receive every claim from every space. Bandwidth is proportional to interest, not node count.

```
GossipDigest:  digest_hex / claim_space / issuer_node_id / witness_count
```

### Witnessing

A witness is not an endorsement. A `WitnessAttestation` with `validation_type: structural` means exactly one thing: “I fetched this object, recomputed its digest, verified the issuer’s signature, and confirmed the schema.” It says nothing about whether the claim is true.

This distinction is load-bearing. A node that witnesses without recomputing is penalized at three times the rate of a publisher whose claim is later challenged — because a lazy witness corrupts the only thing the network relies on for integrity.

```
WitnessAttestation:  digest_hex / witness_node_id / validation_type / timestamp / signature
```

### Challenges

A node that disputes a claim must produce a signed `Challenge` with a declared kind and evidence. Challenges are replayable — any node can fetch a challenge, verify the signature, and evaluate the evidence independently. Dispute history is intrinsic to the claim.

```
Challenge:  target_digest / challenger_node_id / kind / evidence / timestamp / signature
```

Challenge kinds: `DigestMismatch` `InvalidSignature` `InvalidSchema` `MissingEvidenceRef` `ExpiredTTL`

### Executable Claims

An executable claim carries a computation, not just a value. The expression, the input refs it consumed, and the result are all signed and digest-bound. A validator node fetches the input refs, re-runs the expression, and independently verifies the result. A mismatch produces a challenge against the issuer.

Structural witnessing and execution verification are separate acts. A node that attests both issues two attestations with distinct `validation_type` values: `structural` and `compute`.

```
ExecClaim:  claim_space / subject / predicate / expr / exec_kind / input_refs / result / issuer / timestamp
```

Exec kinds: `arithmetic` `inference` `threshold` `derived`

-----

## Claim Spaces

The most important design decision in ANKA is the formal distinction between two kinds of epistemic domain.

**Invariant spaces** admit objective canonicalization. Cryptographic proofs, compiler outputs, deterministic execution traces, typed schemas. Two honest nodes running the same verification always reach the same conclusion. Collapse is computable.

**Interpretive spaces** admit only policy-relative canonicalization. Economic forecasts, medical findings, legal interpretation, scientific consensus in contested domains. No global canonical truth exists. Competing claims coexist indefinitely. A claim set in an interpretive space is not a problem to be resolved — it is a faithful representation of genuine epistemic disagreement.

A `Resolution` object type was considered and rejected. Resolution happens at the policy layer: each consuming node applies its own declared collapse policy to the witness weights, reputation scores, and challenge history the substrate provides. The substrate preserves divergence. The policy node decides what to act on.

-----

## Trust Model

ANKA’s trust model is not permissionless — nodes have declared identities. But it is not permissioned in the traditional sense. Verifiability is open: any node can verify any object against its digest and the issuer’s public key. Authority to publish does not imply authority to be believed.

Reputation is earned per claim space, not globally. A node with high reputation in cryptographic attestation carries no automatic weight in economic forecasting. Reputation decays under failure, floors at zero, and is isolated across spaces.

Witness weight is reputation-derived. Collapse in interpretive spaces is weighted by the accumulated verification history of the witnessing nodes. The network produces local canonical projections — not a single global truth.

-----

## The Invariant

```
∀ n, d, C:
  if node n accepts C for digest d,
  then H(C) = d
```

No node can smuggle an object under the wrong digest. No node can witness without recomputing. No node can challenge without a signed reason. No node can rewrite history without producing a new digest. This is enforced at the transport layer, not by policy.

-----

## Node Roles

|Role     |Permitted Operations                     |
|---------|-----------------------------------------|
|Origin   |publish, witness, register_space, genesis|
|Agent    |publish                                  |
|Validator|witness, challenge                       |
|Archive  |sync, snapshot                           |
|Policy   |collapse, sync                           |

Role declarations are signed objects verifiable by any peer. The origin node is the trust anchor for the mesh — not by fiat, but because its genesis object is verifiable by any joining node against its declared digest.

-----

## Network Properties

**Partition tolerance.** When two nodes partition and publish competing claims on the same subject, both claims survive. On heal, `exchange_once` synchronizes bidirectionally. No claim is silently dropped.

**Scoped gossip.** Nodes declare subscriptions. Gossip is filtered at the sender. At agent scale this is not an optimization — it is a requirement.

**Convergence.** Two nodes that have exchanged all relevant claims produce identical claim sets for any given subject and claim space. Convergence is a provable property of the sync protocol.

**Persistence.** Live node processes back state to SQLite. Identity, claim store, witness log, challenge log, peer list, registry, and audit archive survive process restarts.

-----

## What Is Proven

164 tests passing. 3,301 lines of Fard. The following properties are verified in live multi-process tests, not simulations:

- **5-node full mesh convergence.** One published claim propagates automatically to all five nodes via gossip, fetch, verify, and witness. 5/5 nodes converge. 4/5 issue structural witnesses. No manual intervention.
- **Scoped gossip across live mesh.** Econ-subscribed nodes receive zero science claims. Science-subscribed nodes receive zero econ claims. Wildcard nodes receive both. Bandwidth is proportional to subscription, not mesh size.
- **Policy-collapsed answers with provenance.** `GET /query/{claim_space}/{subject}` returns the winner, scores, and full provenance of all competing claims in a single call.
- **Full audit trail.** Every publish, witness, and challenge automatically appended to the claim trail. Queryable by digest via `GET /audit/trail/{digest}`.
- **Ed25519 across the full protocol.** Every claim, witness, challenge, role declaration, collapse result, and replication receipt is signed with an asymmetric key. Cross-node verification requires no shared secret.
- **Registry bootstrap.** A node joining cold fetches the genesis registry from the origin and discovers all registered claim spaces via chain-verified sync.
- **Partition and heal.** No claims silently dropped after partition. Full convergence after heal.
- **Adversarial simulation.** Lazy witnesses, droppers, and honest nodes coexist. Penalty model enforced. Convergence measured.

-----

## Quickstart

**Requirements:** [Fard](https://github.com/mauludsadiq/FARD) runtime installed.

```bash
git clone https://github.com/mauludsadiq/Anka && cd Anka
fardrun run --program anka/src/origin_process.fard --out out/origin &
fardrun run --program anka/src/node_process.fard --out out/node &
sleep 2

# Register with origin
curl -X POST http://localhost:18080/peer \
  -H "Content-Type: application/json" \
  -d '{"address":"http://localhost:18090"}'

# Fetch claim space registry
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

# Query with policy collapse and provenance
curl http://localhost:18080/query/anka.interpretive.econ/GDP_Q3_2026

# Or use the Fard SDK
import("sdk") as sdk
let c = sdk.client("http://localhost:18080")
let result = sdk.query(c, "anka.interpretive.econ", "GDP_Q3_2026")

# Inspect the audit trail
curl http://localhost:18080/audit/trail/{digest_hex}
```

-----

## Deployment Scenario

An economics research group at Oxford and a quantitative group at MIT both use AI systems to produce GDP forecasts. They want outputs to be independently verifiable and disagreements structurally recorded.

**Setup:**

- Each institution runs a node process behind a TLS reverse proxy per `DEPLOYMENT.md`
- Each node declares an identity binding its Ed25519 key to the institution, department, and role
- Both nodes register with a shared origin and fetch the claim space registry
- Each subscribes to `anka.interpretive.econ`

**Operation:**

- Oxford’s AI publishes its forecast as a signed claim. MIT’s AI publishes its.
- Each node’s validator automatically fetches, verifies, and witnesses the other’s claim
- Reputation accumulates per-node per-claim-space based on verification history

**Query:**

```bash
GET /query/anka.interpretive.econ/GDP_Q3_2026
```

Returns both forecasts, their witness scores, the policy winner, and the full provenance of each. Any downstream system — including another AI — can verify the result independently against the digest.

No central coordinator. No shared database. No trust assumption beyond the genesis registry.

-----

## Why Not X

**Why not a database?** Requires a trusted operator. In ANKA, the claim’s digest is its verification. No operator can tamper with a claim without producing a new digest that won’t match what peers have already witnessed.

**Why not IPFS?** IPFS addresses content but adds no epistemic layer. It cannot tell you who made a claim, whether it was independently verified, or whether it was contested.

**Why not a blockchain?** Blockchains require global consensus, which is expensive and slow, and treat all claims as equivalent. ANKA explicitly preserves disagreement in interpretive domains. Collapse happens at the policy layer per consuming node, not globally.

**Why not a vector database with citations?** Citation tracking is passive. ANKA is active — nodes recompute results, issue signed attestations, file structured challenges. A claim’s witness history reflects actual independent verification.

**Why now?** AI systems are moving from single-model outputs to multi-agent pipelines where claims pass between systems with no attestation. The attack surface for hallucinated provenance is growing faster than the tools to detect it.

-----

## Node API

**Claims**

```
POST /publish                          Publish a signed claim to the mesh
GET  /claim/{digest}                   Fetch a claim envelope by digest
GET  /query/{claim_space}/{subject}    Policy-collapsed answer with full provenance
POST /gossip                           Receive a gossip digest from a peer
POST /fetch                            Fetch, verify, and witness a claim by digest
```

**Witnessing and Challenges**

```
POST /witness                          Record a received witness attestation
POST /challenge                        Record a received challenge
```

**Peers and Subscriptions**

```
POST /peer                             Register a peer address
GET  /peers                            List known peers
POST /subscribe                        Set subscription spaces (replaces current list)
GET  /subscriptions                    List current subscriptions
```

**Registry**

```
GET  /registry                         Fetch the local registry snapshot
POST /registry/fetch                   Fetch and apply registry from a peer
POST /registry/gossip                  Receive a registry gossip notification
```

**Audit and State**

```
GET  /audit                            Archive summary
GET  /audit/trail/{digest}             Full epistemic trail for a claim
GET  /sync                             Node state summary
GET  /known                            List of all known digests
GET  /health                           Node health and identity
```

-----

## Running

```bash
# Start the origin node
fardrun run --program anka/src/origin_process.fard --out out/origin

# Start a mesh node
fardrun run --program anka/src/node_process.fard --out out/node

# Run the full test suite
fardrun test --program anka/tests/test_anka_layer1.fard
```

See `DEPLOYMENT.md` for TLS configuration, key management, and multi-institutional bootstrap.

-----

## What Comes Next

The substrate is complete. What comes next is the application layer.

**AI audit trail adapter.** A wrapper that intercepts an LLM’s generation, packages the prompt, inference parameters, and output as an `ExecClaim`, submits it to ANKA, and returns the claim digest alongside the response. Any downstream system can verify the claim’s provenance before acting on it.

**Verifiable RAG.** An agent that refuses to cite a source unless its claim digest has at least three structural witnesses and no open challenges younger than the network’s convergence time. The citation carries a digest, not a URL.

**Multi-institutional mesh.** Separate machines, separate operators, separate claim spaces. A node at Oxford and a node at MIT exchange claims over HTTPS, verify each other’s signatures without shared secrets, and produce policy-collapsed answers under each institution’s declared rules.

**Economic security layer.** For open participation beyond permissioned institutional meshes: publish stakes, witness stakes, challenge stakes. Bad behavior becomes costly without requiring trust.

# License

MUI 