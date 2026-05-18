# ANKA Interact Protocol — v1.0

## Overview

The ANKA Interact Protocol defines how an ANKA node communicates with an
institution's AI agent. Any institution can implement this protocol to become
addressable by LLMs and other AI systems via ANKA.

## Discovery

An institution publishes its agent endpoint via the ANKA registry:

    POST /runtime/registry
    {
      "name":             "the-gap",
      "address":          "https://agent.gap.com",
      "node_id":          "ed25519:<public_key>",
      "institution_type": "retail",
      "alias":            "gap"
    }

ANKA resolves `gap` -> `the-gap` -> `https://agent.gap.com`.

Alternatively, discovery via well-known URL:

    GET https://gap.com/.well-known/anka.json
    {
      "institution":   "the-gap",
      "interact_url":  "https://agent.gap.com/interact",
      "manifest_url":  "https://agent.gap.com/manifest",
      "protocol":      "anka-interact/1.0"
    }

## Endpoints

### GET /manifest

Returns institution capabilities. No auth required.

Response:
    {
      "ok":               true,
      "institution":      "the-gap",
      "agent_kind":       "retail",
      "protocol_version": "1.0",
      "interact_url":     "https://agent.gap.com/interact",
      "capabilities":     ["retail_return", "order_status", "refund_inquiry"],
      "auth":             "bearer" | "signed_capability" | "none"
    }

### POST /interact

Core protocol endpoint. Institution's AI receives intent and context,
returns structured action and result.

Request:
    {
      "session_id":   "sess-abc123",       // ANKA-issued session ID
      "actor_id":     "user-alice",        // who is acting
      "institution":  "the-gap",           // target institution
      "intent":       "I need to return my jeans",  // natural language
      "capability":   "retail_return",     // scoped capability
      "context":      {                    // structured facts
        "order_id":   "ORDER-9421",
        "item_id":    "JEANS-32x30"
      },
      "timestamp_unix_secs": 1775900000,
      "auth": {                            // optional
        "kind":  "bearer",
        "token": "..."
      }
    }

Response (required fields):
    {
      "ok":           true | false,
      "session_id":   "sess-abc123",
      "action":       "return_authorized",  // machine-readable action taken
      "result":       { ... },              // structured result (action-specific)
      "message":      "Return approved...", // human-readable response
      "receipt_hint": "sha256:...",         // digest for Bay2 receipt (optional)
      "done":         true | false          // is session complete?
    }

Response (on error/rejection):
    {
      "ok":         false,
      "session_id": "sess-abc123",
      "action":     "return_rejected",
      "result":     { "reason": "order not found" },
      "message":    "Sorry, I couldn't find order ORDER-9421.",
      "done":       true
    }

## Standard Actions

### Retail
- return_authorized    result: { return_label_id, refund_amount_cents, refund_method, estimated_refund_days }
- return_rejected      result: { reason }
- order_status_returned result: { order_id, status, delivered_on }
- refund_issued        result: { refund_id, amount_cents, method }

### University
- transcript_issued    result: { document_id, recipient, format, issued_at }
- enrollment_verified  result: { student_id, status, program, expected_graduation }
- identity_required    result: {}  done: false  (multi-turn: ask for identity)

### Government / Research
- constant_returned    result: { name, symbol, value, unit, uncertainty, source }
- dataset_reference_returned result: { dataset_id, url, format, license }

### Universal
- intent_not_understood result: {}  done: false  (multi-turn: clarify)
- session_expired       result: {}  done: true
- auth_required         result: { auth_kind }  done: false

## Multi-Turn Sessions

If `done: false`, the session remains open. ANKA sends another
POST /interact with the same session_id and updated context.

Example — NYU requires identity before issuing transcript:

    Turn 1:
      intent: "I need a transcript"
      -> action: identity_required, done: false

    Turn 2 (same session_id):
      intent: "My student ID is N12345678"
      context: { student_id: "N12345678" }
      -> action: transcript_issued, done: true

## Receipt Protocol

When `receipt_hint` is returned, ANKA optionally writes a Bay2 object:

    POST bay2/object
    {
      "kind":    "anka.interact.receipt",
      "payload": {
        "session_id":   "sess-abc123",
        "institution":  "the-gap",
        "action":       "return_authorized",
        "receipt_hint": "sha256:...",
        "timestamp":    1775900000
      },
      "author_id":          "anka-node",
      "timestamp_unix_secs": 1775900000
    }

This creates a verifiable, content-addressed record of every interaction.

## Implementation Notes

- Institution implements POST /interact in any language
- Response must be JSON with Content-Type: application/json
- HTTP 200 for both ok:true and ok:false (use ok field, not status code)
- HTTP 4xx/5xx only for infrastructure failures (auth, rate limit, down)
- No session state required on institution side — ANKA holds session state
- receipt_hint should be sha256 of (session_id + action + primary result field)

## Reference Implementation

Mock agents in Fard: anka/src/runtime/agents/
Agent server: anka/src/runtime/agent_server.fard (port 19100)

To implement for your institution:
1. Implement GET /manifest
2. Implement POST /interact
3. Register your address in ANKA registry or publish /.well-known/anka.json
4. Test with: curl -X POST {your_url}/interact -d @anka/tests/interact_sample.json
