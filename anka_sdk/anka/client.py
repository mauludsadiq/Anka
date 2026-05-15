from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib import error, request

from .exec_claim import ExecClaim
from .exceptions import (
    AnkaConnectionError,
    AnkaHTTPError,
    AnkaNotFoundError,
    AnkaRateLimitError,
)


class AnkaClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}

        if body is not None:
            data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(url, data=data, headers=headers, method=method)

        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                raise AnkaNotFoundError(exc.code, "not found", raw) from exc
            if exc.code == 429:
                raise AnkaRateLimitError(exc.code, "rate limited", raw) from exc
            raise AnkaHTTPError(exc.code, exc.reason, raw) from exc
        except error.URLError as exc:
            raise AnkaConnectionError(str(exc.reason)) from exc
        except TimeoutError as exc:
            raise AnkaConnectionError("request timed out") from exc

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def known(self) -> Dict[str, Any]:
        return self._request("GET", "/known")

    def sync(self) -> Dict[str, Any]:
        return self._request("GET", "/sync")

    def audit(self) -> Dict[str, Any]:
        return self._request("GET", "/audit")

    def registry(self) -> Dict[str, Any]:
        return self._request("GET", "/registry")

    def peers(self) -> Dict[str, Any]:
        return self._request("GET", "/peers")

    def subscriptions(self) -> Dict[str, Any]:
        return self._request("GET", "/subscriptions")

    def fetch_claim(self, digest_hex: str) -> Dict[str, Any]:
        return self._request("GET", f"/claim/{digest_hex}")

    def audit_trail(self, digest_hex: str) -> Dict[str, Any]:
        return self._request("GET", f"/audit/trail/{digest_hex}")

    def publish(
        self,
        claim_space: str,
        subject: str,
        predicate: str,
        object: Any,
        evidence_refs: Optional[List[str]] = None,
        timestamp_unix_secs: int = 0,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/publish",
            {
                "claim_space": claim_space,
                "subject": subject,
                "predicate": predicate,
                "object": object,
                "evidence_refs": evidence_refs or [],
                "timestamp_unix_secs": timestamp_unix_secs,
            },
        )


    def publish_exec_claim(self, exec_claim: ExecClaim, timestamp_unix_secs: int = 0) -> Dict[str, Any]:
        return self.publish(**exec_claim.to_publish_args(timestamp_unix_secs=timestamp_unix_secs))

    def add_peer(self, address: str) -> Dict[str, Any]:
        return self._request("POST", "/peer", {"address": address})

    def subscribe(self, spaces: List[str]) -> Dict[str, Any]:
        return self._request("POST", "/subscribe", {"spaces": spaces})

    def fetch_registry(self, sender_address: str) -> Dict[str, Any]:
        return self._request("POST", "/registry/fetch", {"sender_address": sender_address})

    def query(self, claim_space: str, subject: str, mode: str = "plural", timestamp_unix_secs: int = 0) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/collapse",
            {
                "claim_space": claim_space,
                "subject": subject,
                "envelopes": [],
                "witnesses": [],
                "mode": mode,
                "timestamp_unix_secs": timestamp_unix_secs,
            },
        )

    def collapse(
        self,
        claim_space: str,
        subject: str,
        envelopes: Optional[List[Dict[str, Any]]] = None,
        witnesses: Optional[List[Dict[str, Any]]] = None,
        mode: str = "plural",
        timestamp_unix_secs: int = 0,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/collapse",
            {
                "claim_space": claim_space,
                "subject": subject,
                "envelopes": envelopes or [],
                "witnesses": witnesses or [],
                "mode": mode,
                "timestamp_unix_secs": timestamp_unix_secs,
            },
        )
