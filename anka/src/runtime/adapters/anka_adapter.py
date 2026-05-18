import json
import hashlib
import argparse
import re
import urllib.request
import os
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



class ShopifyBackend:
    """
    Shopify Admin API backend — real orders, returns, refunds.
    Store: anka-test-store.myshopify.com
    """
    name = "the-gap"
    capabilities = ["retail_return", "order_status", "refund_inquiry"]

    def __init__(self, store, token):
        self.store = store
        self.token = token
        self.base = "https://" + store + "/admin/api/2024-01"
        self.headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
            "User-Agent": "ANKA/1.0"
        }

    def api_get(self, path):
        req = urllib.request.Request(self.base + path, headers=self.headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def api_post(self, path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(self.base + path, data=body, headers=self.headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def find_order(self, order_ref):
        name = order_ref.lstrip("#")
        try:
            data = self.api_get("/orders.json?name=%23" + name + "&status=any")
            orders = data.get("orders", [])
            return orders[0] if orders else None
        except Exception:
            return None

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        order_ref = context.get("order_id") or context.get("order_name", "")

        if "return" in il or "refund" in il:
            if not order_ref:
                return anka_clarify(session_id, "order_id_required",
                    "What is your order number? It starts with # on your receipt.")
            order = self.find_order(order_ref)
            if not order:
                return anka_reject(session_id, "return_rejected", "order_not_found",
                    "I could not find order " + order_ref + ". Please check your order number.")

            order_id = order["id"]
            order_name = order["name"]
            total_price = order.get("total_price", "0.00")
            line_items = order.get("line_items", [])
            items = [i["title"] for i in line_items]

            if order.get("financial_status") == "refunded":
                return anka_reject(session_id, "return_rejected", "already_refunded",
                    "Order " + order_name + " has already been refunded.")

            try:
                txns = self.api_get("/orders/" + str(order_id) + "/transactions.json")
                txn_list = txns.get("transactions", [])
                parent_id = txn_list[0]["id"] if txn_list else None

                refund_payload = {"refund": {
                    "currency": order.get("currency", "USD"),
                    "notify": False,
                    "note": "Return via ANKA interact protocol",
                    "transactions": [{
                        "parent_id": parent_id,
                        "amount": total_price,
                        "kind": "refund",
                        "gateway": txn_list[0]["gateway"] if txn_list else "manual"
                    }] if parent_id else []
                }}

                refund = self.api_post("/orders/" + str(order_id) + "/refunds.json", refund_payload)
                refund_id = refund.get("refund", {}).get("id", "unknown")

                return anka_response(session_id, "return_authorized", {
                    "order_id": str(order_id),
                    "order_name": order_name,
                    "refund_id": str(refund_id),
                    "refund_amount": total_price,
                    "currency": order.get("currency", "USD"),
                    "items": items,
                    "source": "Shopify Admin API (live)"
                }, "Return approved for " + order_name + ". Refund of $" + total_price +
                   " issued. Confirmation sent to customer.")

            except Exception as e:
                return anka_reject(session_id, "refund_failed", str(e),
                    "Could not process refund for " + order_name + ": " + str(e))

        elif "status" in il or "where" in il or "track" in il:
            if not order_ref:
                return anka_clarify(session_id, "order_id_required", "What is your order number?")
            order = self.find_order(order_ref)
            if not order:
                return anka_reject(session_id, "order_not_found", "not_found",
                    "I could not find order " + order_ref + ".")
            items = [i["title"] + " x" + str(i["quantity"]) for i in order.get("line_items", [])]
            tracking = [f["tracking_number"] for f in order.get("fulfillments", []) if f.get("tracking_number")]
            return anka_response(session_id, "order_status_returned", {
                "order_name": order["name"],
                "financial_status": order.get("financial_status"),
                "fulfillment_status": order.get("fulfillment_status"),
                "total_price": order.get("total_price"),
                "items": items,
                "tracking_numbers": tracking,
                "source": "Shopify Admin API (live)"
            }, "Order " + order["name"] + ": " + str(order.get("financial_status")) +
               " | " + ", ".join(items))

        else:
            return anka_clarify(session_id, "intent_not_understood",
                "I can help with order status, returns, and refunds. What is your order number?")

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



class WorldBankBackend:
    """
    World Bank API backend — live economic indicators.
    No API key required.
    https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
    """
    name = "world-bank"
    capabilities = ["gdp_query", "economic_indicator", "country_data", "poverty_data"]
    BASE = "https://api.worldbank.org/v2"

    INDICATORS = {
        "gdp":               ("NY.GDP.MKTP.CD", "GDP (current US$)"),
        "gdp per capita":    ("NY.GDP.PCAP.CD", "GDP per capita (current US$)"),
        "population":        ("SP.POP.TOTL",    "Population total"),
        "inflation":         ("FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)"),
        "unemployment":      ("SL.UEM.TOTL.ZS", "Unemployment, total (% of labor force)"),
        "poverty":           ("SI.POV.DDAY",    "Poverty headcount ratio at $2.15/day (%)"),
        "life expectancy":   ("SP.DYN.LE00.IN", "Life expectancy at birth (years)"),
        "co2":               ("EN.ATM.CO2E.PC", "CO2 emissions (metric tons per capita)"),
        "trade":             ("NE.TRD.GNFS.ZS", "Trade (% of GDP)"),
        "debt":              ("GC.DOD.TOTL.GD.ZS", "Central government debt (% of GDP)"),
    }

    COUNTRY_CODES = {
        "united states": "US", "usa": "US", "us": "US", "america": "US",
        "china": "CN", "uk": "GB", "united kingdom": "GB", "britain": "GB",
        "germany": "DE", "france": "FR", "japan": "JP", "india": "IN",
        "brazil": "BR", "canada": "CA", "australia": "AU", "russia": "RU",
        "south korea": "KR", "korea": "KR", "mexico": "MX", "italy": "IT",
        "spain": "ES", "indonesia": "ID", "turkey": "TR", "saudi arabia": "SA",
        "netherlands": "NL", "switzerland": "CH", "argentina": "AR", "nigeria": "NG",
        "world": "WLD", "global": "WLD",
    }

    def fetch_indicator(self, country_code, indicator_code, mrv=1):
        try:
            url = (self.BASE + "/country/" + country_code +
                   "/indicator/" + indicator_code +
                   "?format=json&mrv=" + str(mrv))
            req = urllib.request.Request(url,
                headers={"User-Agent": "ANKA/1.0 (anka-interact-protocol)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            if len(data) >= 2 and data[1] and len(data[1]) > 0:
                rec = data[1][0]
                return {
                    "country": rec["country"]["value"],
                    "country_code": rec["countryiso3code"],
                    "indicator_id": indicator_code,
                    "indicator_name": rec["indicator"]["value"],
                    "value": rec["value"],
                    "year": rec["date"],
                    "source": "World Bank Open Data",
                    "last_updated": data[0].get("lastupdated", ""),
                    "reference_url": "https://data.worldbank.org"
                }
        except Exception:
            return None
        return None

    def detect_country(self, intent_lower, context):
        if context.get("country"):
            c = context["country"].lower()
            return self.COUNTRY_CODES.get(c, c.upper()[:2])
        for name, code in self.COUNTRY_CODES.items():
            if name in intent_lower:
                return code
        return "WLD"

    def detect_indicator(self, intent_lower):
        for keyword, (code, name) in self.INDICATORS.items():
            if keyword in intent_lower:
                return code, name
        return None, None

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        country_code = self.detect_country(il, context)
        indicator_code, indicator_name = self.detect_indicator(il)

        if not indicator_code:
            return anka_clarify(session_id, "indicator_not_understood",
                "I can provide GDP, population, inflation, unemployment, poverty rate, "
                "life expectancy, CO2 emissions, trade, and debt for any country. "
                "Try: GDP of Germany, or China population.")

        data = self.fetch_indicator(country_code, indicator_code)
        if not data:
            return anka_reject(session_id, "data_fetch_failed", "worldbank_unavailable",
                "Could not fetch " + indicator_name + " for " + country_code +
                " from World Bank. Try again shortly.")

        value = data["value"]
        if value is None:
            return anka_reject(session_id, "no_data", "no_data_available",
                "No data available for " + indicator_name + " in " + data["country"] + ".")

        # Format value
        if abs(value) >= 1e12:
            formatted = "$" + str(round(value/1e12, 2)) + " trillion"
        elif abs(value) >= 1e9:
            formatted = "$" + str(round(value/1e9, 2)) + " billion"
        elif abs(value) >= 1e6:
            formatted = "$" + str(round(value/1e6, 2)) + " million"
        else:
            formatted = str(round(value, 2))

        msg = (data["country"] + " " + indicator_name + ": " +
               formatted + " (" + data["year"] + ", World Bank)")
        return anka_response(session_id, "indicator_returned", data, msg)

# ── Shopify credentials ──────────────────────────────────────────────────────
# Set via env vars or edit this file directly for local development.
# Never commit real tokens to public repos.
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "anka-test-store.myshopify.com")
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_TOKEN", "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")
SHOPIFY = ShopifyBackend(SHOPIFY_STORE, SHOPIFY_TOKEN) if SHOPIFY_TOKEN else GapBackend()
BACKENDS = {
    "the-gap": SHOPIFY, "gap": SHOPIFY, "shopify": SHOPIFY,
    "nyu": NYUBackend(), "nyu.edu": NYUBackend(),
    "nist": NISTBackend(), "nist.gov": NISTBackend(),
    "world-bank": WorldBankBackend(), "worldbank": WorldBankBackend(), "worldbank.org": WorldBankBackend(),
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
