# ANKA

**The AI-facing institutional layer. The protocol that lets AI act on your behalf.**

```bash
git clone https://github.com/mauludsadiq/Anka && cd Anka
bash demo.sh
```

---

## The Problem

You were in a car accident. You need to file a police report, submit an insurance claim, and book a repair appointment.

Today you spend 3 hours on hold, filling duplicate forms, getting contradictory answers from bots that don't talk to each other. Information is lost. Nothing is auditable. You are the integration layer.

**This is not a chatbot problem. It is an infrastructure problem.**

Every institution has AI. None of them can talk to each other with verifiable provenance.

---

## The Demo

```
User: "I was in a car accident yesterday. The other driver ran a red light.
       I need help with the insurance claim, my car repair, and the police report."
```

```
Step 1: Police report RPT-* filed. Officer Rodriguez assigned.
Step 2: Claim CLM-* approved. $2,531.51 (CPI 2.9%, World Bank 2024, live).
Step 3: Repair booked 2026-05-21 at 10:00 AM. Estimate $2,350.

All actions signed, content-addressed, and recorded in the ANKA mesh.
No forms. No phone trees. No lost paperwork.
```

Agents are discovered dynamically from the mesh — not hardcoded. Any institution
can register. The mesh routes to the best available agent per capability.

The payout uses live US CPI data from the World Bank API at runtime.

**Run it:**

```bash
bash demo.sh        # accident demo in ~60 seconds
bash demo-full.sh   # all four demos
```

---

## The Mesh Is the Memory

The user comes back the next day:

```
User: "What is the status of my claim?"
ANKA: CLM-* approved. $2,531.51. Repair booked May 21.

User: "Can I move the repair to Friday?"
ANKA: Rescheduled to Friday May 22 at 10:00 AM. Recorded: anka:sha256:e206...
```

No session cookie. No database query. No AI memory. The state lives in the mesh -
signed, content-addressed, queryable by anyone with the digest.

```bash
python3 anka/demos/accident_flow_dynamic.py   # turn 1
python3 anka/demos/accident_followup.py       # turns 2 and 3
```

---

## Live Institution Integrations

Five real APIs, no mocks, running inside Docker containers:

    NIST        Planck constant = 6.62607015e-34 J Hz^-1   physics.nist.gov (CODATA 2022)
    World Bank  US GDP = $28.75 trillion (2024)             api.worldbank.org
    Shopify     real orders and refunds                     anka-test-store.myshopify.com
    PubMed      4,061 papers on mRNA vaccine efficacy       pubmed.ncbi.nlm.nih.gov
    arXiv       17,992 preprints on large language models   export.arxiv.org

---

## Research Verification (100% Live)

```
User: "I am publishing a paper on climate sensitivity.
       Help me verify my key claims and find related work."
```

```
  arXiv:      26 preprints      export.arxiv.org (live)
  PubMed:     24,665 papers     pubmed.ncbi.nlm.nih.gov (live)
  NIST:       Stefan-Boltzmann = 5.67e-8 W m^-2 K^-4 (CODATA 2022, live)
  World Bank: Global GDP = $110.98 trillion (2024, live)

  arXiv search    anka:sha256:059ec13a...
  PubMed search   anka:sha256:3cd58665...
  NIST constants  anka:sha256:43c3c497...
  World Bank data anka:sha256:e4a6e4d9...
```

```bash
python3 anka/demos/research_verification_flow.py
```

---

## Agent Discovery

Agents register capabilities as signed claims in the ANKA mesh.
Dalil queries the mesh to route to the best agent per capability.

```
POST /register              agent registers: police_report | Chicago
GET  /discover/police_report  -> city-pd @ http://... (score: N witnesses)
```

Any agent can register. Any institution can join. The mesh routes intelligently.
New agents raise the score of capabilities they cover. Bad agents get slashed.

---

## The Stack

    Bay2    operational substrate     object storage, streams, replay, metering
    ANKA    epistemic coordination    claims, witnesses, collapse, audit
    Dalil   AI-native browser         browse, read, trail, discover, compose
    Raqib   autonomous agent runtime  identity, memory, observe, deliberate, act

---

## The Analogy

    ARPANET was the protocol. The killer app was the Web.
    The Web was the protocol. The killer app was Mosaic.
    LLMs are the technology. The killer app was ChatGPT.
    ANKA is the protocol. Dalil is the browser. Raqib is the agent.

---

## Repositories

    https://github.com/mauludsadiq/Anka     13,590 lines   152 files
    https://github.com/mauludsadiq/Bay2      2,825 lines    25 files
    https://github.com/mauludsadiq/Raqib     1,071 lines    10 files
    https://github.com/mauludsadiq/Dalil       798 lines     4 files
    https://github.com/mauludsadiq/stack-pilot  one-command demo

    Total: 18,284 lines of Fard across 191 files

---

## Docker

    docker compose up

Services: origin, alice, bob, adapter (Python), demo.
The demo container proves the full epistemic mesh and all five live integrations.
Exit code: 0.

---

## Node API

    POST /publish                          Publish a signed claim
    GET  /query/{claim_space}/{subject}    Collapsed answer with full provenance
    POST /witness                          Record a witness attestation
    POST /challenge                        Record a challenge
    GET  /audit/trail/{digest}             Full epistemic trail for a claim
    GET  /health                           Node health and identity
    GET  /dashboard                        Live operator dashboard
    POST /runtime/interact                 Route intent to institution agent
    GET  /runtime/sessions                 All sessions with audit trail

Full API: see DEPLOYMENT.md

---

## Language

Written in Fard - a deterministic functional language for verifiable
AI-operated systems. Every computation is reproducible. Every claim is
content-addressed. Every operation is replayable.

    https://github.com/mauludsadiq/FARD

---

## License

MUI
