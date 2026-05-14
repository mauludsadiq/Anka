# ANKA

A network substrate built for AI systems. Written in [Fard](https://github.com/mauludsadiq/FARD).

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

**Faithful disagreement.** Competing claims about the same subject coexist as first-class objects. Contradiction is a relation, not an error. Collapse is a deliberate policy act under declared rules, not a default resolution.

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

Gossip is scoped. Nodes declare which claim spaces they subscribe to. Digests outside that subscription are not sent.

-----

## Claim Spaces

Two kinds, formally distinct at the registry level.

**Invariant spaces** — canonicalization is objective. Hashes, proofs, compiler outputs, cryptographic attestations. Two nodes always agree on the result.

**Interpretive spaces** — canonicalization is policy-relative. Economics, medicine, legal interpretation, scientific forecasting. These do not collapse globally — only under local policy, trust weighting, and witness preference. That is not a limitation. It is an honest representation of how knowledge works.

The same subject in different claim spaces never collides. Namespace isolation is enforced at the registry.

-----

## Object Model

```
ClaimSet          claim_space / subject / predicate / object / evidence_refs / issuer / timestamp / signature
GossipDigest      digest_hex / claim_space / issuer_node_id / witness_count
WitnessAttestation  digest_hex / witness_node_id / validation_type / timestamp / signature
Challenge         target_digest / challenger_node_id / kind / evidence / timestamp / signature
```

Challenge kinds: `DigestMismatch` `InvalidSignature` `InvalidSchema` `MissingEvidenceRef` `ExpiredTTL`

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
GET  /health
```

-----

## First Invariant

```
∀ n, d, C:
  if node n accepts C for digest d,
  then H(C) = d
```

No node can smuggle an object under the wrong digest. No node can witness without recomputing. No node can challenge without a signed reason. No node can rewrite history without producing a new digest.

-----

## Deployment Model

ANKA nodes have declared identities. The mesh is permissioned by identity, open by verifiability.

**Origin node** — defines genesis registry, publishes first claim spaces, witnesses initial protocol objects.

**Agent nodes** — AI systems that publish claims, attach evidence and execution traces, consume claim sets for retrieval and reasoning.

**Validator nodes** — verify structure, signatures, and execution traces. Issue witnesses. File challenges.

**Archive nodes** — preserve canonical objects, claim sets, registry versions, and receipts. Provide reconstruction.

**Policy nodes** — perform local collapse under explicit declared policy. Do not decide global truth.

-----

## Simulation

Scenarios are declared as JSON and drive the full network run — nodes, claim spaces, claims, witnesses, challenges, and collapse policy per node.

```bash
fardrun run --program anka/src/sim_runner.fard --out out/sim
```

-----

## Status

82 tests. 1,829 lines of Fard. Origin node live with verified genesis. Two mesh nodes exchanging claims over the wire.

The substrate is complete: canonical identity, signed transport, scoped gossip, structural witnessing, semantic challenge, reputation-weighted collapse, partition-tolerant convergence, executable claims with independent execution verification, persistent live processes, a real two-node mesh with outbound gossip broadcast, and an origin node that boots genesis, registers default claim spaces, and serves a verifiable bootstrap object to any joining node.

# License

MUI