# ANKA

A network substrate built for AI systems.

The World Wide Web was built for humans fetching documents. URLs are locations, not identities. Provenance is external. Disagreement has no formal structure. Truth judgments are implicit and unattributable.

ANKA is built differently.

-----

## Core Principle

```
identity = H(canonical object)
```

Before truth, you need identity. Before identity, you need integrity. ANKA establishes both at the protocol layer.

A digest is not a pointer to content. It *is* the content’s identity. The same object always produces the same digest. A different digest is a different object. There is no ambiguity.

-----

## What ANKA Solves

**Stable identity.** On the web, the same URL can return different content over time. Different URLs can return the same content. In ANKA, the same digest always means the same canonical object.

**Intrinsic provenance.** Web provenance is bolted on — citations, screenshots, archives, PKI added after the fact. In ANKA, every claim carries its own epistemic trail: signature, witness history, challenge history, reconstruction path. The object knows where it has been.

**Machine-native verification.** The web assumes humans read, interpret, and judge. AI systems cannot operate efficiently that way. ANKA changes the primitive from `fetch page → infer meaning` to `fetch canonical object → verify directly`.

**Explicit contestability.** The web has disagreement but no formal dispute layer. ANKA makes contestability first-class protocol structure: claim, witness, challenge, resolution, reputation impact.

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

## Claim Spaces

ANKA distinguishes two fundamentally different kinds of claim space at the registry level.

**Invariant spaces** — canonicalization is objective. Examples: hashes, theorem proofs, compiler outputs, cryptographic attestations, typed schemas. These are computably collapsible. Two nodes will always agree on the result.

**Interpretive spaces** — canonicalization is policy-relative. Examples: economics, medicine, journalism, legal interpretation, scientific forecasting. These do not collapse globally. They collapse only under local policy, trust weighting, and witness preference.

This means a single global canonical truth `Z_global` does not exist for interpretive domains. Instead ANKA produces `Z^(policy)` — local canonical projections. That is not a limitation. It is an honest representation of how knowledge actually works.

The same subject in different claim spaces never collides. Namespace isolation is enforced at the registry layer.

-----

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

## Current Status

32 tests passing across all layers. The full substrate is operational.

- Multi-node canonical object propagation is live
- Competing claims and contradiction relations are first-class
- Plural and single-winner collapse modes are both supported
- Invariant and interpretive claim spaces are formally distinct at the registry level
- Node state snapshots deterministically and restores cleanly

Witnessing is structural in v1. Collapse policy, witness weight, reputation mechanics, and policy-relative convergence are the next layers.

-----

## What ANKA Is Not

ANKA is not a replacement for HTTP. It is an epistemic routing layer — a semantic transport protocol where the network object is not content but *verifiable claim state*.

The web solved the problem of moving documents between humans. ANKA solves the problem of moving claims between agents.