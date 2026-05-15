# ANKA

**A verifiable claim substrate for autonomous AI systems.**

Written in [Fard](https://github.com/mauludsadiq/FARD).

![Tests](https://img.shields.io/badge/tests-164%20passing-brightgreen)
![Lines](https://img.shields.io/badge/lines-3%2C301-blue)
![Language](https://img.shields.io/badge/language-Fard-purple)
![Roadmap](https://img.shields.io/badge/roadmap-8%2F8%20phases-brightgreen)
![Status](https://img.shields.io/badge/status-active-success)

-----

## The Problem

AI systems are producing high-stakes claims — research findings, medical recommendations, legal analysis, financial forecasts — with no infrastructure for verifying where those claims came from, who checked them, or whether they were contested.

The current workarounds are bad. RAG systems cite URLs that change. Fine-tuned models inherit training data provenance that nobody can reconstruct. Agents pass outputs between each other with no attestation layer. When something goes wrong, there is no trail.

This is not a model problem. It is an infrastructure problem. The internet has no native primitive for a verifiable claim — a statement with intrinsic provenance, independent verification, and a contestation record that survives the session that produced it.

ANKA is that primitive.

-----

## Quickstart

**Requirements:** [Fard](https://github.com/mauludsadiq/FARD) runtime installed.

```bash
# Clone and start an origin node
git clone https://github.com/mauludsadiq/Anka && cd Anka
fardrun run --program anka/src/origin_process.fard --out out/origin &
fardrun run --program anka/src/node_process.fard --out out/node &
sleep 2

# Register peer
curl -X POST http://localhost:18080/peer \
  -H "Content-Type: application/json" \
  -d '{"address":"http://localhost:18090"}'

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

# Query the collapsed result with provenance
curl http://localhost:18080/query/anka.interpretive.econ/GDP_Q3_2026

# Inspect the full audit trail
curl http://localhost:18080/audit/trail/{digest_hex}
```

The published claim is automatically gossiped to peers, fetched, verified against its digest, and witnessed. The query endpoint returns the policy-collapsed answer with scores and full provenance in a single call.

-----

## The Primitive

```
identity = H(canonical object)
```

Every object in ANKA has an identity that is its content. The digest is not a pointer — it *is* the thing. Two objects with the same digest are the same object. An object with a different digest is a different object. There is no indirection, no mutable reference, no update-in-place.

**H** is SHA-256 over the canonical JSON serialization of the object. The hash function is declared in the genesis registry and is not extensible at runtime. A claim space that uses a different hash function is a different claim space, not a version of this one. Identity is not parameterized.

This gives the network three properties that HTTP cannot provide:

1. **Stable identity.** A digest always refers to exactly one object, across all nodes, across all time.
1. **Intrinsic provenance.** Every object carries its own epistemic trail. Signatures, witnesses, challenges, and reconstruction paths are part of the object, not metadata attached elsewhere.
1. **Tamper evidence without a central authority.** Any node can verify any object against its digest without asking anyone’s permission.

-----

## Architecture

ANKA is an epistemic routing layer. The network object is not content — it is *verifiable claim state*.

### Claims

A claim is a signed statement: a subject, a predicate, an object, a set of evidence references, an issuer identity, and a timestamp. The claim is canonically serialized and hashed to produce its digest. The issuer signs the digest. The envelope — claim plus digest plus signature — is the atomic unit of the network.

```
ClaimSet:  claim_space / subject / predicate / object / evidence_refs / issuer_node_id / timestamp / signature
```

### Gossip

Nodes gossip digests, not payloads. When a node publishes a claim, it announces the digest to its peers. Peers fetch the full envelope only if the claim falls within their declared subscription. This is the difference between a mesh and a broadcast network — at agent scale, no node should receive every claim from every space.

```
GossipDigest:  digest_hex / claim_space / issuer_node_id / witness_count
```

### Witnessing

A witness is not an endorsement. A `WitnessAttestation` with `validation_type: structural` means exactly one thing: “I fetched this object, recomputed its digest, verified the issuer’s signature, and confirmed the schema.” It says nothing about whether the claim is true.

This distinction is load-bearing. The witness layer is the verification layer. A node that witnesses without recomputing is penalized at three times the rate of a publisher whose claim is later challenged — because a lazy witness corrupts the only thing the network relies on for integrity.

```
WitnessAttestation:  digest_hex / witness_node_id / validation_type / timestamp / signature
```

### Challenges

A node that disputes a claim cannot simply assert disagreement. It must produce a signed `Challenge` with a declared kind and evidence. Challenges are replayable — any node can fetch a challenge, verify the challenger’s signature, and evaluate the evidence independently. Dispute history is intrinsic to the claim.

```
Challenge:  target_digest / challenger_node_id / kind / evidence / timestamp / signature
```

Challenge kinds: `DigestMismatch` `InvalidSignature` `InvalidSchema` `MissingEvidenceRef` `ExpiredTTL`

### Executable Claims

An executable claim carries a computation, not just a value. The expression, the input refs it consumed, and the result are all signed and digest-bound. A validator node fetches the input refs, re-runs the expression, and independently verifies the result. A mismatch produces a challenge against the issuer.

Structural witnessing and execution verification are separate acts. A structural witness faces no penalty if an executable claim later fails recomputation — that challenge is against the claim’s issuer. A node that wishes to attest both structural validity and execution correctness issues two attestations with distinct `validation_type` values: `structural` and `compute`.

```
ExecClaim:  claim_space / subject / predicate / expr / exec_kind / input_refs / result / issuer / timestamp
```

Exec kinds: `arithmetic` `inference` `threshold` `derived`

-----

## Claim Spaces

The most important design decision in ANKA is the formal distinction between two kinds of epistemic domain.

**Invariant spaces** admit objective canonicalization. Cryptographic proofs, compiler outputs, deterministic execution traces, typed schemas. Two honest nodes running the same verification always reach the same conclusion. Collapse is computable.

**Interpretive spaces** admit only policy-relative canonicalization. Economic forecasts, medical findings, legal interpretation, scientific consensus in contested domains. No global canonical truth exists. Competing claims coexist indefinitely. A claim set in an interpretive space is not a problem to be resolved — it is a faithful representation of genuine epistemic disagreement.

A `Resolution` object type was considered and rejected. It would introduce a false appearance of global settlement in domains where no global settlement exists. Instead, resolution happens at the **policy layer**: each consuming node applies its own declared collapse policy to the witness weights, reputation scores, and challenge history the substrate provides. The substrate preserves divergence. The policy node decides what to act on.

The same subject in different claim spaces never collides. Namespace isolation is enforced at the registry layer.

-----

## Trust Without Centralization

ANKA’s trust model is not permissionless — nodes have declared identities. But it is not permissioned in the traditional sense either. Verifiability is open: any node can verify any object against its digest and the issuer’s known public identity. Authority to publish does not imply authority to be believed.

Reputation is earned per claim space, not globally. A node with high reputation in cryptographic attestation carries no automatic weight in economic forecasting. Reputation decays under failure, floors at zero weight (discredited nodes become silent, not adversarial), and is isolated across spaces.

Witness weight is reputation-derived. Collapse in interpretive spaces is weighted by the accumulated verification history of the witnessing nodes. The network produces local canonical projections — `Z^(policy)` — not a single global truth.

-----

## The Invariant

```
∀ n, d, C:
  if node n accepts C for digest d,
  then H(C) = d
```

No node can smuggle an object under the wrong digest. No node can witness without recomputing. No node can challenge without a signed reason. No node can rewrite history without producing a new digest.

This is enforced at the transport layer. Tampered envelopes are rejected before acceptance. Unknown peers are rejected before processing. The invariant is structural, not policy.

-----

## Node Roles

Nodes declare roles as signed objects. Role declarations are verifiable by any peer.

|Role     |Permitted Operations                     |
|---------|-----------------------------------------|
|Origin   |publish, witness, register_space, genesis|
|Agent    |publish                                  |
|Validator|witness, challenge                       |
|Archive  |sync, snapshot                           |
|Policy   |collapse, sync                           |

The origin node defines the genesis registry, publishes the first claim spaces, and witnesses the initial protocol objects. It is the trust anchor for the mesh — not by fiat, but because its genesis object is verifiable by any joining node against its declared digest.

-----

## Network Properties

**Partition tolerance.** When two nodes partition and publish competing claims on the same subject, both claims survive. On partition heal, `exchange_once` synchronizes known digests bidirectionally. No claim is silently dropped. The resulting claim set contains both, with their full witness and challenge histories intact.

**Scoped gossip.** Nodes declare subscriptions to specific claim spaces. Gossip is filtered at the sender — a validator specializing in cryptographic proofs does not receive economic forecast digests. At agent scale this is not an optimization; it is a requirement.

**Convergence.** Two nodes that have exchanged all relevant claims produce identical claim sets for any given subject and claim space. Convergence is a provable property of the sync protocol, not an eventual consistency hope.

**Persistence.** Live node processes back state to SQLite. Identity, claim store, witness log, challenge log, peer list, and registry survive process restarts. A node that restarts rejoins the mesh with full prior state.

-----

## Implementation

164 tests. 3,301 lines of [Fard](https://github.com/mauludsadiq/FARD). No external dependencies beyond the Fard standard library.

**Scoped gossip verified across live 5-node mesh.** Nodes with `econ.space` subscriptions receive only economic claims. Nodes with `science.space` subscriptions receive only science claims. Wildcard nodes receive both. Science-only nodes receive zero economic claims and vice versa. The mesh scales by interest — nodes receive only what they declare they want. This is not a simulation.

**5-node live mesh verified.** Five separate processes, five separate SQLite databases, five separate node identities. One published claim propagates automatically to all five nodes via gossip, fetch, verify, and witness — without manual intervention. 5/5 nodes converge. 4/5 issue structural witnesses (the publisher does not witness its own claims). This is not a simulation — it is five fardrun processes communicating over HTTP.

The stack, bottom to top:

```
Canonical serialization and digest
Message signing and verification
Transport with peer authentication and tamper rejection
Peer sync with digest-first selective fetch
Claim publication, gossip, and envelope acceptance
Structural witnessing and challenge filing
Claim sets with contradiction relations and collapse modes
Claim space registry with versioned objects
Context-scoped reputation with witness weight
Semantic challenge resolution
Weighted collapse under declared policy
Executable claims with independent execution verification
Partition-tolerant convergence
Scoped gossip with subscription filtering
Archive with claim trails and reconstruction
Node roles with signed declarations
Origin node with verified genesis bootstrap
Live HTTP node processes with persistent state
Two-node mesh with outbound gossip broadcast
```

Each layer enforces its own invariant. No layer trusts the one below blindly.

## Why Not X

**Why not a database?** A database requires a trusted operator. Any node can query ANKA without trusting the node it queries — the claim’s digest is its verification. The operator cannot tamper with a claim without producing a new digest that won’t match what peers have already witnessed.

**Why not IPFS or a content-addressed store?** IPFS addresses content but adds no epistemic layer. It cannot tell you who made a claim, whether it was independently verified, or whether it was contested. ANKA adds witnessing, challenge, reputation, and policy-collapsed consensus on top of content addressing.

**Why not a blockchain?** Blockchains require global consensus, which is expensive and slow, and they treat all claims as equivalent. ANKA explicitly preserves disagreement in interpretive domains — a competing forecast is not a conflict to resolve, it is information to retain. Collapse happens at the policy layer per consuming node, not globally.

**Why not a vector database with citations?** Citation tracking is append-only and passive. ANKA is active — nodes recompute results, issue signed attestations, file structured challenges. A claim’s witness history reflects actual independent verification, not just storage.

**Why now?** AI systems are moving from single-model outputs to multi-agent pipelines where claims pass between systems with no attestation. The attack surface for hallucinated provenance is growing faster than the tools to detect it. ANKA is the missing substrate layer.

-----

-----

## Node API

Every live node exposes the following HTTP endpoints.

**Claims**

```
POST /publish                          Publish a signed claim to the mesh
GET  /claim/{digest}                   Fetch a specific claim envelope by digest
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
GET  /audit                            Archive summary (snapshot count, receipt count)
GET  /audit/trail/{digest}             Full epistemic trail for a claim digest
GET  /sync                             Node state summary (claim, witness, challenge counts)
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

# Run a parameterized simulation
fardrun run --program anka/src/sim_runner.fard --out out/sim

# Run the full test suite
fardrun test --program anka/tests/test_anka_layer1.fard
```

-----

## Deployment Scenario

A computational economics group at Oxford and a quantitative research group at MIT both use AI systems to produce GDP forecasts. They want their outputs to be independently verifiable and their disagreements to be structurally recorded.

**Setup (one hour):**

- Each institution runs a node process behind a TLS-terminating reverse proxy per `DEPLOYMENT.md`
- Each node declares an identity binding its Ed25519 key to the institution and department
- Both nodes register with a shared origin node and fetch the claim space registry
- Each node subscribes to `anka.interpretive.econ`

**Operation:**

- Oxford’s AI publishes its forecast as a signed claim. MIT’s AI publishes its.
- Each node’s validator automatically fetches, verifies, and witnesses the other’s claim
- Reputation accumulates per-node per-claim-space based on verification history
- A policy node applies weighted collapse under declared rules

**Consumption:**

```bash
GET /query/anka.interpretive.econ/GDP_Q3_2026
```

Returns: both forecasts, their witness scores, the policy winner, and the full provenance of each — issuer identity, evidence references, timestamps, verification history. Any downstream system, including another AI, can verify the result independently against the digest.

**No central coordinator. No shared database. No trust assumption beyond the genesis registry.**

-----

## What ANKA Is For

ANKA is a substrate where divergent intelligent agents can coordinate without pretending to a unitary reality, while converging where it matters.

The internet assumes a human at the end of every chain — someone who reads, judges, and takes responsibility. AI systems cannot operate on that assumption. They need a network where:

- **Provenance is intrinsic.** Not metadata attached elsewhere. Not a trusted intermediary vouching. The claim carries its own origin, evidence, and verification history.
- **Disagreement is preserved faithfully.** When two research groups produce conflicting findings, both survive in the mesh — with their full evidence and witness histories — until a consuming agent applies its own declared policy to decide what to act on.
- **Verification is computable.** A validator node doesn’t read a claim and trust it. It fetches the evidence references, re-runs the computation, and independently confirms the result. A mismatch produces a signed challenge that any other node can verify.
- **Coordination happens without consensus.** Interpretive domains — science, economics, law, medicine — don’t converge to a single truth. ANKA doesn’t pretend they do. It preserves the divergence and makes the structure of disagreement legible.

The intended deployment contexts are institutions where AI systems generate high-stakes claims: research universities, hospitals, financial institutions, legal systems. A claim about a drug interaction, an economic forecast, a legal interpretation, a code verification result. Any of these needs provenance, witness history, and contestation records that survive the lifecycle of the claim — not just the session that produced it.

The substrate is complete. What comes next is the application layer.

## What Comes Next

**AI audit trail adapter.** A wrapper that intercepts an LLM’s generation, packages the prompt, inference parameters, and output as an `ExecClaim`, submits it to ANKA, and returns the claim digest alongside the response. Any downstream system can verify the claim’s provenance and check its witness history before acting on it.

**Verifiable RAG.** An agent that refuses to cite a source unless its claim digest has at least three structural witnesses and no open challenges younger than the network’s convergence time. The citation carries a digest, not a URL. The reader can independently verify.

**Multi-institutional mesh.** Separate machines, separate operators, separate claim spaces. A node at Oxford and a node at MIT exchange claims over HTTPS, verify each other’s signatures without shared secrets, and produce policy-collapsed answers under each institution’s declared rules. No central coordinator.

**Economic security layer.** In a permissioned institutional mesh, reputation and identity declarations provide sufficient Sybil resistance. For open participation, a staking and slashing layer — publish stakes, witness stakes, challenge stakes — makes bad behavior costly without requiring trust.

# License

MUI 