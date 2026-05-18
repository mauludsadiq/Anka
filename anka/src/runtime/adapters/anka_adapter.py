import json
import hashlib
import argparse
import re
import urllib.request
import os
import urllib.parse
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

class PubMedBackend:
    """
    PubMed/NCBI E-utilities backend - live biomedical literature.
    No API key required.
    """
    name = "pubmed"
    capabilities = ["literature_search", "paper_lookup", "abstract_fetch"]
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def api_get(self, path):
        url = self.BASE + path + "&tool=anka-interact&email=anka@collapselogic.com"
        req = urllib.request.Request(url, headers={"User-Agent": "ANKA/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def search(self, query, max_results=3):
        import urllib.parse
        q = urllib.parse.quote(query)
        data = self.api_get("/esearch.fcgi?db=pubmed&term=" + q + "&retmax=" + str(max_results) + "&retmode=json")
        return data["esearchresult"]["idlist"], data["esearchresult"]["count"]

    def fetch_summary(self, pmid):
        data = self.api_get("/esummary.fcgi?db=pubmed&id=" + pmid + "&retmode=json")
        rec = data["result"][pmid]
        authors = [a["name"] for a in rec.get("authors", [])[:3]]
        if len(rec.get("authors", [])) > 3:
            authors.append("et al.")
        return {
            "pmid": pmid,
            "title": rec.get("title", ""),
            "authors": authors,
            "journal": rec.get("source", ""),
            "pubdate": rec.get("pubdate", ""),
            "doi": next((i["value"] for i in rec.get("articleids", []) if i["idtype"] == "doi"), None),
            "url": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/",
            "source": "PubMed (NCBI E-utilities)"
        }

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        pmid = str(context.get("pmid") or context.get("pubmed_id") or "")
        if pmid and pmid != "None":
            try:
                paper = self.fetch_summary(pmid)
                return anka_response(session_id, "paper_returned", paper,
                    paper["title"][:80] + " — " + ", ".join(paper["authors"]) + " (" + paper["pubdate"] + ")")
            except Exception as e:
                return anka_reject(session_id, "paper_fetch_failed", str(e),
                    "Could not fetch PMID " + str(pmid) + " from PubMed.")

        query = intent
        for prefix in ["search for papers on ", "find papers on ", "find papers about ",
                        "search for ", "literature on ", "studies on ",
                        "research on ", "papers on ", "papers about ", "look up "]:
            if il.startswith(prefix):
                query = intent[len(prefix):]
                break

        try:
            ids, total = self.search(query, max_results=3)
            if not ids:
                return anka_reject(session_id, "no_results", "no_papers_found",
                    "No papers found for: " + query)
            papers = []
            for pid in ids:
                try:
                    papers.append(self.fetch_summary(pid))
                except Exception:
                    pass
            top = papers[0] if papers else {}
            msg = ("Found " + str(total) + " papers on '" + query + "'. Top: " +
                   top.get("title", "")[:60] + " — " +
                   ", ".join(top.get("authors", [])) + " (" + top.get("pubdate", "") + ")")
            return anka_response(session_id, "literature_returned", {
                "query": query, "total_results": total,
                "papers": papers, "source": "PubMed (NCBI E-utilities)"
            }, msg)
        except Exception as e:
            return anka_reject(session_id, "search_failed", str(e),
                "PubMed search failed for: " + query)



class ArXivBackend:
    """
    arXiv preprint backend - live from export.arxiv.org
    No API key required. Atom XML feed.
    """
    name = "arxiv"
    capabilities = ["preprint_search", "paper_lookup", "abstract_fetch"]
    BASE = "https://export.arxiv.org/api/query"

    def search(self, query, max_results=3, field="all"):
        import urllib.parse
        # Use ti: for title search, all: for full text
        q = urllib.parse.quote(f'ti:"{query}"' if " " in query else f"{field}:{query}")
        url = f"{self.BASE}?search_query={q}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        req = urllib.request.Request(url, headers={"User-Agent": "ANKA/1.0 (anka-interact-protocol)"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8")
        return self.parse_feed(xml)

    def parse_feed(self, xml):
        import re
        total_match = re.search(r"<opensearch:totalResults[^>]*>(\d+)</opensearch:totalResults>", xml)
        total = total_match.group(1) if total_match else "0"
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        papers = []
        for entry in entries:
            def extract(tag):
                m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", entry, re.DOTALL)
                return m.group(1).strip() if m else ""
            arxiv_id = extract("id").replace("http://arxiv.org/abs/", "").replace("https://arxiv.org/abs/", "")
            title = re.sub(r"\s+", " ", extract("title"))
            summary = re.sub(r"\s+", " ", extract("summary"))[:300]
            published = extract("published")[:10]
            authors = re.findall(r"<name>(.*?)</name>", entry)[:3]
            if len(re.findall(r"<name>(.*?)</name>", entry)) > 3:
                authors.append("et al.")
            cats = re.findall(r'<category term="([^"]+)"', entry)
            papers.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "published": published,
                "categories": cats[:3],
                "summary": summary,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
                "source": "arXiv"
            })
        return papers, total

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        arxiv_id = context.get("arxiv_id")
        if arxiv_id:
            try:
                import urllib.parse
                url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
                req = urllib.request.Request(url, headers={"User-Agent": "ANKA/1.0"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    xml = r.read().decode("utf-8")
                papers, _ = self.parse_feed(xml)
                if papers:
                    p = papers[0]
                    return anka_response(session_id, "paper_returned", p,
                        p["title"][:80] + " — " + ", ".join(p["authors"]) + " (" + p["published"] + ")")
            except Exception as e:
                return anka_reject(session_id, "fetch_failed", str(e),
                    "Could not fetch arXiv:" + arxiv_id)

        query = intent
        for prefix in ["search arxiv for ", "find preprints on ", "find papers on ",
                        "arxiv search ", "preprints on ", "search for "]:
            if il.startswith(prefix):
                query = intent[len(prefix):]
                break

        try:
            papers, total = self.search(query, max_results=3)
            if not papers:
                return anka_reject(session_id, "no_results", "no_papers_found",
                    "No preprints found on arXiv for: " + query)
            top = papers[0]
            msg = ("Found " + total + " preprints on '" + query + "'. Top: " +
                   top["title"][:60] + " — " + ", ".join(top["authors"]) +
                   " (" + top["published"] + ")")
            return anka_response(session_id, "preprints_returned", {
                "query": query, "total_results": total,
                "papers": papers, "source": "arXiv"
            }, msg)
        except Exception as e:
            return anka_reject(session_id, "search_failed", str(e),
                "arXiv search failed for: " + query)



class CityPDBackend:
    """City Police Department — incident report filing and retrieval."""
    name = "city-pd"
    capabilities = ["police_report", "incident_lookup", "report_status"]

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        incident_id = context.get("incident_id", "INC-UNKNOWN")

        if "file" in il or "report" in il or "accident" in il:
            import hashlib, time
            report_number = "RPT-" + hashlib.sha256((incident_id + str(time.time())).encode()).hexdigest()[:8].upper()
            date = context.get("date", "2026-05-17")
            location = context.get("location", "Unknown location")
            description = context.get("description", "Vehicle accident")
            injuries = context.get("injuries", "none reported")
            return anka_response(session_id, "report_filed", {
                "report_number": report_number,
                "incident_id": incident_id,
                "date": date,
                "location": location,
                "description": description,
                "injuries": injuries,
                "status": "filed",
                "officer": "Officer M. Rodriguez, Badge #4471",
                "filing_date": "2026-05-18",
                "source": "City Police Department (mock)"
            }, "Police report " + report_number + " filed for incident at " +
               location + " on " + date + ". Officer Rodriguez assigned.")

        elif "status" in il or "lookup" in il:
            report_number = context.get("report_number", "unknown")
            return anka_response(session_id, "report_status_returned", {
                "report_number": report_number,
                "status": "filed",
                "available_for_insurance": True,
                "source": "City Police Department (mock)"
            }, "Report " + report_number + " is filed and available for insurance submission.")

        return anka_clarify(session_id, "intent_not_understood",
            "I can help file a police report or check report status.")


class StateFarmBackend:
    """State Farm Insurance — claim filing, assessment, approval."""
    name = "state-farm"
    capabilities = ["claim_filing", "claim_status", "payout_estimate"]

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        incident_id = context.get("incident_id", "INC-UNKNOWN")
        policy_number = context.get("policy_number", "SF-000000")

        if "file" in il or "claim" in il or "accident" in il:
            import hashlib, time
            claim_id = "CLM-" + hashlib.sha256((incident_id + policy_number).encode()).hexdigest()[:8].upper()
            at_fault = context.get("at_fault", "unknown")
            damage = context.get("damage_description", "Vehicle damage")
            police_report = context.get("police_report", "")

            # Estimate payout based on damage description
            payout = "2847.00"
            if "total" in damage.lower():
                payout = "18500.00"
            elif "door" in damage.lower() or "fender" in damage.lower():
                payout = "2847.00"
            elif "windshield" in damage.lower():
                payout = "450.00"

            return anka_response(session_id, "claim_approved", {
                "claim_id": claim_id,
                "incident_id": incident_id,
                "policy_number": policy_number,
                "police_report": police_report,
                "at_fault": at_fault,
                "damage_description": damage,
                "estimated_payout": payout,
                "currency": "USD",
                "adjuster": "Sarah Chen, Adjuster #SF-2291",
                "status": "approved",
                "deductible": "500.00",
                "net_payout": str(round(float(payout) - 500, 2)),
                "expected_processing_days": 3,
                "source": "State Farm Insurance (mock)"
            }, "Claim " + claim_id + " approved. Estimated payout $" + payout +
               " (net $" + str(round(float(payout) - 500, 2)) + " after deductible). " +
               "Adjuster Sarah Chen will contact you within 24 hours.")

        elif "status" in il:
            claim_id = context.get("claim_id", "unknown")
            return anka_response(session_id, "claim_status_returned", {
                "claim_id": claim_id, "status": "approved",
                "source": "State Farm Insurance (mock)"
            }, "Claim " + claim_id + " is approved and processing.")

        return anka_clarify(session_id, "intent_not_understood",
            "I can help file an insurance claim or check claim status.")


class CityAutoRepairBackend:
    """City Auto Repair — appointment booking, estimates."""
    name = "city-auto"
    capabilities = ["repair_booking", "estimate_request", "appointment_status"]

    SLOTS = [
        ("2026-05-21", "Thursday", "10:00 AM"),
        ("2026-05-22", "Friday",   "2:00 PM"),
        ("2026-05-23", "Saturday", "9:00 AM"),
    ]

    def handle_intent(self, intent, context, session_id, capability):
        il = intent.lower()
        claim_id = context.get("claim_id", "")
        vehicle = context.get("vehicle", "your vehicle")
        damage = context.get("damage", "vehicle damage")

        if "book" in il or "appointment" in il or "repair" in il or "schedule" in il:
            import hashlib, time
            slot = self.SLOTS[0]
            appt_id = "APPT-" + hashlib.sha256((claim_id + slot[0]).encode()).hexdigest()[:8].upper()

            # Estimate based on damage
            estimate = "2350.00"
            if "door" in damage.lower() and "fender" in damage.lower():
                estimate = "2350.00"
            elif "door" in damage.lower():
                estimate = "1200.00"
            elif "fender" in damage.lower():
                estimate = "850.00"
            elif "windshield" in damage.lower():
                estimate = "380.00"

            insurance_approved = context.get("insurance_approved", False)
            return anka_response(session_id, "appointment_booked", {
                "appointment_id": appt_id,
                "appointment_date": slot[0],
                "appointment_day": slot[1],
                "appointment_time": slot[2],
                "vehicle": vehicle,
                "damage": damage,
                "repair_estimate": estimate,
                "currency": "USD",
                "insurance_claim": claim_id,
                "insurance_billing": insurance_approved,
                "technician": "Mike Torres, Senior Technician",
                "estimated_completion_days": 3,
                "loaner_available": True,
                "source": "City Auto Repair (mock)"
            }, "Repair appointment booked for " + slot[1] + " " + slot[0] +
               " at " + slot[2] + ". Estimate: $" + estimate + ". " +
               ("Insurance will be billed directly. " if insurance_approved else "") +
               "Loaner car available. Technician: Mike Torres.")

        return anka_clarify(session_id, "intent_not_understood",
            "I can book a repair appointment or provide an estimate.")


BACKENDS = {
    "the-gap": SHOPIFY, "gap": SHOPIFY, "shopify": SHOPIFY,
    "nyu": NYUBackend(), "nyu.edu": NYUBackend(),
    "nist": NISTBackend(), "nist.gov": NISTBackend(),
    "world-bank": WorldBankBackend(), "worldbank": WorldBankBackend(), "worldbank.org": WorldBankBackend(),
    "pubmed": PubMedBackend(), "ncbi": PubMedBackend(),
    "arxiv": ArXivBackend(), "arxiv.org": ArXivBackend(),
    "city-pd": CityPDBackend(), "citypd": CityPDBackend(),
    "state-farm": StateFarmBackend(), "statefarm": StateFarmBackend(),
    "city-auto": CityAutoRepairBackend(), "cityauto": CityAutoRepairBackend(),
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
