# ANKA

A network substrate built for AI systems. Written in [Fard](https://github.com/fardrun/fard).

-----

## Core Principle

```
identity = H(canonical object)
```

Before truth, you need identity. Before identity, you need integrity. ANKA establishes both at the protocol layer.

A digest is not a pointer to content. It *is* the content’s identity. The same object always produces the same digest. A different digest is a different object. There is no ambiguity.

-----

## What ANKA Solves

**Stable identity.** The same digest always means the same canonical object. No ambiguity about what an object is or was.

**Intrinsic provenance.** Every claim carries its own epistemic trail: signature, witness history, challenge history, reconstruction path. The object knows where it has been. Provenance is not bolted on after the fact — it is native to the object.

**Machine-native verification.** ANKA changes the primitive from `fetch page → infer meaning` to `fetch canonical object → verify directly`. Built for autonomous systems that cannot rely on human interpretation as a step in the pipeline.

**Explicit contestability.** Disagreement is first-class protocol structure: claim, witness, challenge, resolution, reputation impact. The network does not paper over conflict — it represents it faithfully.

**Faithful disagreement.** Competing claims about the same subject coexist as first-class objects. Contradiction is a relation, not an error. Collapse is a deliberate policy act, not a default.

-----

## Network Flow

```
Node A publishes ClaimSet
        |
        v
Node A gossips digest only          ← thin gossip; payload not assumed relevant
        |
        v
Node B requests full object
        |
        v
Node B verifies:
  - digest matches payload
  - signature valid
  - schema valid
  - issuer key valid
        |
        v
Node B signs WitnessAttestation     ← "I verified this structurally"
        |
        v
Node B gossips witness
        |
        v
Node C syncs digest + witness set   ← knows the object without holding it
```

-----

## Claim Spaces

ANKA distinguishes two fundamentally different kinds of claim space at the registry level.

**Invariant spaces** — canonicalization is objective. Examples: hashes, theorem proofs, compiler outputs, cryptographic attestations, typed schemas. These are computably collapsible. Two nodes will always agree on the result.

**Interpretive spaces** — canonicalization is policy-relative. Examples: economics, medicine, journalism, legal interpretation, scientific forecasting. These do not collapse globally. They collapse only under local policy, trust weighting, and witness preference.

A single global canonical truth does not exist for interpretive domains. Instead ANKA produces local canonical projections under declared policy. That is not a limitation — it is an honest representation of how knowledge actually works.

The same subject in different claim spaces never collides. Namespace isolation is enforced at the registry layer.

-----

## Object Model

### ClaimSet

```rust
pub struct ClaimSet {
    pub claim_space: String,
    pub subject: String,
    pub predicate: String,
    pub object: String,
    pub evidence_refs: Vec<String>,
    pub issuer_node_id: String,
    pub timestamp_unix_secs: u64,
    pub signature_hex: String,
}
```

### GossipDigest

```rust
pub struct GossipDigest {
    pub digest_hex: String,
    pub claim_space: String,
    pub issuer_node_id: String,
    pub witness_count: u64,
}
```

### WitnessAttestation

```rust
pub struct WitnessAttestation {
    pub digest_hex: String,
    pub witness_node_id: String,
    pub validation_type: String,   // structural | compute | semantic
    pub timestamp_unix_secs: u64,
    pub signature_hex: String,
}
```

### Challenge

```rust
pub struct Challenge {
    pub target_digest_hex: String,
    pub challenger_node_id: String,
    pub kind: ChallengeKind,
    pub evidence: String,
    pub timestamp_unix_secs: u64,
    pub signature_hex: String,
}

pub enum ChallengeKind {
    DigestMismatch,
    InvalidSignature,
    InvalidSchema,
    MissingEvidenceRef,
    ExpiredTTL,
}
```

-----

## Node API

```
POST /publish
POST /gossip
GET  /claim/{digest}
POST /witness
POST /challenge
GET  /sync
GET  /known
```

-----

## Stack

```
Message layer     sign / verify / encode
      ↓
Transport layer   peer identity / tamper rejection
      ↓
Peer sync         digest discovery / selective fetch
      ↓
Layer 1           claim / witness / challenge / sync
      ↓
Claim sets        competing claims / contradiction relations / collapse modes
      ↓
Claim spaces      invariant vs interpretive / registry / namespace isolation
      ↓
Store layer       deterministic snapshot / write / restore
      ↓
Reputation        per-space pass/fail history / witness weight / floor at zero
      ↓
Simulation        generated node identities / parameterized scenarios / configurable collapse policy
```

Each layer enforces its own invariant. No layer trusts the one below blindly.

-----

## First Invariant

```
∀ n, d, C:
  if node n accepts C for digest d,
  then H(C) = d
```

No node can smuggle an object under the wrong digest. No node can witness without recomputing. No node can challenge without a signed reason. No node can rewrite history without producing a new digest.

-----

## Simulation

Scenarios are declared as JSON and drive the full network run — node count, claim spaces, claims, witness assignments, challenge rules, and collapse policy per node. Node identities are generated fresh on every run.

```json
{
  "name": "economic divergence: two competing GDP forecasts",
  "nodes": [
    { "id": "node-a", "collapse_policy": "plural" },
    { "id": "node-b", "collapse_policy": "plural" },
    { "id": "node-c", "collapse_policy": "single-winner" }
  ],
  "claim_spaces": [...],
  "claims": [...],
  "witnesses": [...],
  "challenges": [...]
}
```

```bash
fardrun run --program anka/src/sim_runner.fard --out out/sim
```

-----

## Current Status

43 tests passing, plus an enhanced interpretive mesh demo. 1,216 lines of Fard across 21 source files.

- Multi-node canonical object propagation live
- Signed message layer live
- Signed wire transport layer live
- Peer sync planning live
- Deterministic node state snapshots live
- Claim-space registry live with versioned objects and deterministic genesis
- Registry witness anchors registry digest
- Invariant and interpretive claim spaces formally distinct
- Competing claims and contradiction relations first-class
- Plural and single-winner local collapse supported
- Context-scoped reputation live
- Semantic challenge resolution live
- Simulation deterministic: same scenario produces identical digests across runs
- Enhanced demo shows interpretive divergence, witnesses, challenge, local collapse policies, and reputation effects

Next layers:

- Add weighted collapse
- Add executable/inference claims
- Add live multi-node processes