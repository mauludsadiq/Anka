# ANKA — First Network Layer in FARD

ANKA v0.1 implements the first substrate layer of an AI-native claim mesh in FARD.

This layer intentionally avoids semantic truth decisions. It proves the transport invariant first:

```text
canonical object -> digest -> thin gossip -> fetch -> verify -> witness -> challenge -> sync
```

## Network invariant

```text
If a node accepts a claim envelope for digest d, then sha256(canonical_claim) == d.
```

## Included modules

```text
anka/src/canonical.fard    canonical JSON + digest functions
anka/src/claim.fard        ClaimSet and ClaimEnvelope constructors/verifiers
anka/src/gossip.fard       thin digest gossip messages
anka/src/witness.fard      structural witness attestations
anka/src/challenge.fard    structural challenge objects
anka/src/node.fard         in-memory ANKA node state and protocol functions
anka/src/demo.fard         runnable three-node substrate demo
anka/tests/test_anka_layer1.fard   executable tests
```

## Run

From this directory:

```bash
fardrun test --program anka/tests/test_anka_layer1.fard
fardrun run --program anka/src/demo.fard --out out/demo
```

## Layer 1 scope

Supported in this first layer:

- deterministic canonical claim serialization
- SHA-256 digest derivation
- node identity as deterministic key text for local simulation
- signed issuer envelope simulation via SHA-256 commitment
- thin gossip digest announcements
- full claim fetch from local store
- structural verification
- structural witness signing
- structural challenge construction
- peer sync by digest/witness/challenge records

Not included in v0.1:

- semantic truth adjudication
- live TCP/HTTP service
- economic slashing
- persistent SQLite store
- Ed25519 node keys
- policy tensors

Those belong after the object propagation invariant is proven.
