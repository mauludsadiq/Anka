import json
import hashlib
import argparse
import re
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


def anka_response(session_id, action, result, message, ok=True, done=True):
    receipt = hashlib.sha256((session_id + ":" + action).encode()).hexdigest()
    return {"ok": ok, "session_id": session_id, "action": action,
            "result": result, "message": message,
            "receipt_hint": "sha256:" + receipt, "done": done}

def anka_reject(session_id, action, reason, message):
    return anka_response(session_id, action, {"reason": reason}, message, ok=False, done=True)

def anka_clarify(session_id, action, message):
    return anka_response(session_id, action, {}, message, ok=False, done=False)


class GapBackend:
    name = "the-gap"
    capabilities = ["retail_return", "order_status", "refund_inquiry"]

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        order_id = context.get("order_id", "")
        item_id = context.get("item_id", "")
        if "return" in il or "refund" in il:
            if not order_id or not order_id.startswith("ORDER-"):
                return anka_reject(session_id, "return_rejected", "invalid_order_id",
                    "I could not find order " + repr(order_id) + ". Please check your order number.")
            price = context.get("price_cents", 4999)
            label = "LABEL-UPS-" + order_id.replace("ORDER-", "")
            return anka_response(session_id, "return_authorized", {
                "order_id": order_id, "item_id": item_id,
                "return_label_id": label, "refund_amount_cents": price,
                "refund_method": "original_payment", "estimated_refund_days": 3,
                "carrier": "UPS", "tracking_url": "https://ups.com/track/" + label
            }, "Return approved for " + order_id + ". Label " + label +
               " emailed to you. Refund of $" + str(price/100) + " in 3-5 days.")
        elif "status" in il or "where" in il:
            if not order_id:
                return anka_clarify(session_id, "order_id_required", "What is your order number?")
            return anka_response(session_id, "order_status_returned",
                {"order_id": order_id, "status": "delivered", "delivered_on": "2026-04-10"},
                "Order " + order_id + " was delivered on April 10, 2026.")
        else:
            return anka_clarify(session_id, "intent_not_understood",
                "I can help with returns, refunds, and order status. What do you need?")


class NYUBackend:
    name = "nyu"
    capabilities = ["transcript_request", "enrollment_verification", "student_records"]

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        student_id = context.get("student_id", "")
        if not student_id:
            return anka_clarify(session_id, "identity_required",
                "Please provide your NYU NetID or N-number to continue.")
        if "transcript" in il:
            recipient = context.get("recipient", "self")
            doc_id = "NYU-TR-2026-" + student_id[:8]
            return anka_response(session_id, "transcript_issued", {
                "student_id": student_id, "document_id": doc_id,
                "recipient": recipient, "format": "official_pdf",
                "issued_at": "2026-05-17", "tracking_url": "https://parchment.com/track/" + doc_id
            }, "Official transcript " + doc_id + " sent to " + recipient + ".")
        elif "enrollment" in il or "verification" in il:
            return anka_response(session_id, "enrollment_verified",
                {"student_id": student_id, "status": "enrolled",
                 "program": "Computer Science MS", "expected_graduation": "May 2027"},
                "Student " + student_id + " is enrolled in CS MS, graduating May 2027.")
        else:
            return anka_clarify(session_id, "intent_not_understood",
                "I can help with transcripts and enrollment verification.")


class NISTBackend:
    """Live NIST physical constants — fetches real CODATA 2022 data."""
    name = "nist"
    capabilities = ["physical_constants", "dataset_reference", "measurement_standards"]
    NIST_URL = "https://physics.nist.gov/cuu/Constants/Table/allascii.txt"
    ALIASES = {
        "stefan-boltzmann":  "Stefan-Boltzmann constant",
        "stefan":            "Stefan-Boltzmann constant",
        "fine-structure":    "fine-structure constant",
        "fine structure":    "fine-structure constant",
        "speed of light":    "speed of light in vacuum",
        "elementary charge": "elementary charge",
        "electron mass":     "electron mass",
        "proton mass":       "proton mass",
        "gravitational":     "Newtonian constant of gravitation",
        "avogadro":          "Avogadro constant",
        "boltzmann":         "Boltzmann constant",
        "planck":            "Planck constant",
    }

    def fetch_constant(self, query_name):
        try:
            req = urllib.request.Request(self.NIST_URL,
                headers={"User-Agent": "ANKA/1.0 (anka-interact-protocol)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                text = r.read().decode("ascii", errors="ignore")
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped.lower().startswith(query_name.lower()):
                    parts = re.split(r"\s{2,}", stripped)
                    if len(parts) >= 2:
                        value = parts[1].strip().replace(" ", "")
                        uncertainty = parts[2].strip().strip("()") if len(parts) > 2 else "exact"
                        unit = parts[3].strip() if len(parts) > 3 else ""
                        return {"name": parts[0].strip(), "value": value,
                                "uncertainty": uncertainty or "exact", "unit": unit,
                                "source": "NIST CODATA 2022", "codata_year": 2022,
                                "reference_url": "https://physics.nist.gov/cuu/Constants/"}
        except Exception:
            return None
        return None

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        canonical = None
        for keyword, name in self.ALIASES.items():
            if keyword in il:
                canonical = name
                break
        if canonical:
            data = self.fetch_constant(canonical)
            if data:
                msg = (data["name"] + " = " + data["value"] + " " + data["unit"] +
                       " (NIST CODATA " + str(data["codata_year"]) + ")")
                return anka_response(session_id, "constant_returned", data, msg)
            return anka_reject(session_id, "constant_fetch_failed", "nist_unavailable",
                "Could not fetch " + canonical + " from NIST. Try again shortly.")
        if "dataset" in il or "data" in il:
            dataset_id = context.get("dataset_id", "unknown")
            return anka_response(session_id, "dataset_reference_returned",
                {"dataset_id": dataset_id,
                 "url": "https://data.nist.gov/od/id/" + dataset_id,
                 "format": "JSON-LD", "license": "public_domain"},
                "Dataset " + dataset_id + " available at data.nist.gov.")
        return anka_clarify(session_id, "intent_not_understood",
            "I can provide live NIST constants: Planck, Boltzmann, Avogadro, "
            "speed of light, elementary charge, and more.")


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
                "interact_url": "http://localhost:" + str(self.port) + "/interact",
                "capabilities": backend.capabilities if backend else [], "auth": "none"})
        elif path == "/.well-known/anka.json":
            self.send_json({"institution": self.institution,
                "interact_url": "http://localhost:" + str(self.port) + "/interact",
                "manifest_url": "http://localhost:" + str(self.port) + "/manifest",
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
                    "no_backend", "No backend for: " + institution))
                return
            try:
                response = backend.handle_intent(intent, context, session_id, capability)
                print("  [" + institution + "] " + intent[:50] + " -> " + response["action"])
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
    print("ANKA adapter: " + institution + " on :" + str(port))
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--institution", default="the-gap")
    parser.add_argument("--port", type=int, default=19200)
    args = parser.parse_args()
    run(args.institution, args.port)
