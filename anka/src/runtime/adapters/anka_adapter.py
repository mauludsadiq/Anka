#!/usr/bin/env python3
"""
ANKA Interact Protocol Adapter — Python Reference Implementation

A thin HTTP server that translates ANKA interact requests into calls
to a company's existing API, then returns ANKA-formatted responses.

Usage:
    python3 anka_adapter.py --institution the-gap --port 19200

The adapter is stateless. ANKA holds session state.
Companies implement the handle_intent function for their domain.
"""

import json
import hashlib
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


def anka_response(session_id, action, result, message, ok=True, done=True):
    receipt = hashlib.sha256(f"{session_id}:{action}".encode()).hexdigest()
    return {"ok": ok, "session_id": session_id, "action": action,
            "result": result, "message": message,
            "receipt_hint": f"sha256:{receipt}", "done": done}

def anka_reject(session_id, action, reason, message):
    return anka_response(session_id, action, {"reason": reason}, message, ok=False, done=True)

def anka_clarify(session_id, action, message):
    return anka_response(session_id, action, {}, message, ok=False, done=False)


class GapBackend:
    name = "the-gap"
    capabilities = ["retail_return", "order_status", "refund_inquiry"]

    def handle_intent(self, intent, context, session_id, capability):
        intent_lower = intent.lower()
        order_id = context.get("order_id", "")
        item_id = context.get("item_id", "")

        if "return" in intent_lower or "refund" in intent_lower:
            if not order_id or not order_id.startswith("ORDER-"):
                return anka_reject(session_id, "return_rejected", "invalid_order_id",
                    f"I couldn't find order '{order_id}'. Please check your order number.")
            price_cents = context.get("price_cents", 4999)
            label_id = f"LABEL-UPS-{order_id.replace('ORDER-', '')}"
            return anka_response(session_id, "return_authorized", {
                "order_id": order_id, "item_id": item_id,
                "return_label_id": label_id, "refund_amount_cents": price_cents,
                "refund_method": "original_payment", "estimated_refund_days": 3,
                "carrier": "UPS", "tracking_url": f"https://ups.com/track/{label_id}"
            }, f"Return approved for {order_id}. Label {label_id} emailed to you. "
               f"Refund of ${price_cents/100:.2f} in 3-5 days.")

        elif "status" in intent_lower or "where" in intent_lower:
            if not order_id:
                return anka_clarify(session_id, "order_id_required", "What's your order number?")
            return anka_response(session_id, "order_status_returned",
                {"order_id": order_id, "status": "delivered",
                 "delivered_on": "2026-04-10", "carrier": "UPS"},
                f"Order {order_id} was delivered on April 10, 2026.")

        else:
            return anka_clarify(session_id, "intent_not_understood",
                "I can help with returns, refunds, and order status. What do you need?")


class NYUBackend:
    name = "nyu"
    capabilities = ["transcript_request", "enrollment_verification", "student_records"]

    def handle_intent(self, intent, context, session_id, capability):
        intent_lower = intent.lower()
        student_id = context.get("student_id", "")

        if not student_id:
            return anka_clarify(session_id, "identity_required",
                "Please provide your NYU NetID or N-number to continue.")

        if "transcript" in intent_lower:
            recipient = context.get("recipient", "self")
            doc_id = f"NYU-TR-2026-{student_id[:8]}"
            return anka_response(session_id, "transcript_issued", {
                "student_id": student_id, "document_id": doc_id,
                "recipient": recipient, "format": "official_pdf",
                "issued_at": "2026-05-17", "delivery": "secure_electronic",
                "tracking_url": f"https://parchment.com/track/{doc_id}"
            }, f"Official transcript {doc_id} sent to {recipient}.")

        elif "enrollment" in intent_lower or "verification" in intent_lower:
            return anka_response(session_id, "enrollment_verified",
                {"student_id": student_id, "status": "enrolled",
                 "program": "Computer Science MS", "expected_graduation": "May 2027"},
                f"Student {student_id} is enrolled in CS MS, graduating May 2027.")

        else:
            return anka_clarify(session_id, "intent_not_understood",
                "I can help with transcripts and enrollment verification.")


class NISTBackend:
    name = "nist"
    capabilities = ["physical_constants", "dataset_reference", "measurement_standards"]

    CONSTANTS = {
        "planck":            {"name": "Planck constant", "symbol": "h", "value": "6.62607015e-34", "unit": "J Hz^-1", "uncertainty": "exact"},
        "boltzmann":         {"name": "Boltzmann constant", "symbol": "k", "value": "1.380649e-23", "unit": "J K^-1", "uncertainty": "exact"},
        "avogadro":          {"name": "Avogadro constant", "symbol": "N_A", "value": "6.02214076e+23", "unit": "mol^-1", "uncertainty": "exact"},
        "speed of light":    {"name": "speed of light", "symbol": "c", "value": "299792458", "unit": "m s^-1", "uncertainty": "exact"},
        "elementary charge": {"name": "elementary charge", "symbol": "e", "value": "1.602176634e-19", "unit": "C", "uncertainty": "exact"},
    }

    def handle_intent(self, intent, context, session_id, capability):
        intent_lower = intent.lower()
        for key, constant in self.CONSTANTS.items():
            if key in intent_lower:
                return anka_response(session_id, "constant_returned",
                    {**constant, "codata_year": 2018,
                     "reference_url": "https://physics.nist.gov/cuu/Constants/"},
                    f"{constant['name']} {constant['symbol']} = {constant['value']} {constant['unit']} (exact, CODATA 2018).")

        if "dataset" in intent_lower or "data" in intent_lower:
            dataset_id = context.get("dataset_id", "unknown")
            return anka_response(session_id, "dataset_reference_returned",
                {"dataset_id": dataset_id,
                 "url": f"https://data.nist.gov/od/id/{dataset_id}",
                 "format": "JSON-LD", "license": "public_domain"},
                f"Dataset {dataset_id} available at data.nist.gov.")

        return anka_clarify(session_id, "intent_not_understood",
            "I can provide physical constants (Planck, Boltzmann, Avogadro, etc.) and dataset references.")


BACKENDS = {
    "the-gap": GapBackend(), "gap": GapBackend(),
    "nyu": NYUBackend(), "nyu.edu": NYUBackend(),
    "nist": NISTBackend(), "nist.gov": NISTBackend(),
}


class ANKAHandler(BaseHTTPRequestHandler):
    institution = "the-gap"
    port = 19200

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        backend = BACKENDS.get(self.institution)
        if path == "/health":
            self.send_json({"ok": True, "kind": "anka_adapter",
                "institution": self.institution, "protocol": "anka-interact/1.0"})
        elif path == "/manifest":
            self.send_json({"ok": True, "institution": self.institution,
                "protocol_version": "1.0",
                "interact_url": f"http://localhost:{self.port}/interact",
                "capabilities": backend.capabilities if backend else [],
                "auth": "none"})
        elif path == "/.well-known/anka.json":
            self.send_json({"institution": self.institution,
                "interact_url": f"http://localhost:{self.port}/interact",
                "manifest_url": f"http://localhost:{self.port}/manifest",
                "protocol": "anka-interact/1.0"})
        else:
            self.send_json({"ok": False, "reason": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        if path == "/interact":
            session_id = body.get("session_id", "unknown")
            intent = body.get("intent", "")
            context = body.get("context", {})
            capability = body.get("capability", "")
            institution = body.get("institution", self.institution)
            backend = BACKENDS.get(institution) or BACKENDS.get(self.institution)
            if not backend:
                self.send_json(anka_reject(session_id, "unknown_institution",
                    "no_backend", f"No backend for: {institution}"))
                return
            try:
                response = backend.handle_intent(intent, context, session_id, capability)
                print(f"  [{institution}] {intent[:50]} -> {response['action']}")
                self.send_json(response)
            except Exception as e:
                self.send_json(anka_reject(session_id, "backend_error",
                    str(e), "An error occurred processing your request."))
        else:
            self.send_json({"ok": False, "reason": "not found"}, 404)


def run(institution, port):
    ANKAHandler.institution = institution
    ANKAHandler.port = port
    server = HTTPServer(("", port), ANKAHandler)
    print(f"ANKA adapter: {institution} on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--institution", default="the-gap")
    parser.add_argument("--port", type=int, default=19200)
    args = parser.parse_args()
    run(args.institution, args.port)
