from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client import AnkaClient


def publish_llm_output(
    client: AnkaClient,
    claim_space: str,
    subject: str,
    output: Any,
    evidence_refs: Optional[List[str]] = None,
    predicate: str = "llm_output",
    timestamp_unix_secs: int = 0,
) -> Dict[str, Any]:
    return client.publish(
        claim_space=claim_space,
        subject=subject,
        predicate=predicate,
        object=output,
        evidence_refs=evidence_refs or [],
        timestamp_unix_secs=timestamp_unix_secs,
    )


class AnkaAgent:
    def __init__(self, client: AnkaClient, claim_space: str):
        self.client = client
        self.claim_space = claim_space

    def publish_output(
        self,
        subject: str,
        output: Any,
        evidence_refs: Optional[List[str]] = None,
        predicate: str = "llm_output",
        timestamp_unix_secs: int = 0,
    ) -> Dict[str, Any]:
        return publish_llm_output(
            self.client,
            claim_space=self.claim_space,
            subject=subject,
            output=output,
            evidence_refs=evidence_refs,
            predicate=predicate,
            timestamp_unix_secs=timestamp_unix_secs,
        )
