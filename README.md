# ANKA

**A verifiable claim substrate for autonomous AI systems.**

Written in [FARD](https://github.com/mauludsadiq/FARD).

-----

## The Problem

The internet was built for humans fetching documents. Its trust primitives — domain names, TLS certificates, HTML pages — assume a human at the end of the chain who reads, interprets, and judges.

AI systems cannot operate on that assumption. An autonomous agent cannot “just read the page.” It needs to know: who made this claim, when, on what evidence, who verified it, who contested it, and whether the reasoning behind it can be independently replicated. None of that is native to HTTP.

The result is that AI systems today either hallucinate provenance, inherit the trust assumptions of whatever human-readable system they’re scraping, or require trusted centralized intermediaries to vouch for information quality. None of these scale. None of them are honest about uncertainty. And none of them support the kind of structured disagreement that complex domains — science, economics, law, medicine — actually exhibit.

ANKA is built on a different primitive.

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

112 tests. 2,096 lines of [FARD](https://github.com/mauludsadiq/FARD). No external dependencies beyond the Fard standard library.

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

## What Comes Next

The substrate is complete. The next layer is the application: an agent mesh where AI systems publish claims with execution traces, validator nodes recompute and attest, archive nodes preserve the full epistemic trail, and policy nodes collapse under declared rules.

The natural first application is an audit trail for AI-generated claims — a network where the provenance, verification history, and contestation record of any AI output is intrinsic to the output itself, not stored separately, not dependent on a trusted intermediary, and not losable.

# License

MUI 