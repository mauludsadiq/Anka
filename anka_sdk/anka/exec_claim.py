from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def value_digest(value: Any) -> str:
    return sha256_text(canonical_json(value))


@dataclass(frozen=True)
class ExecInput:
    name: str
    digest: str
    media_type: str = "application/json"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "digest": self.digest,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class ExecOutput:
    value: Any
    media_type: str = "application/json"
    digest: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        digest = self.digest or value_digest(self.value)
        return {
            "digest": digest,
            "media_type": self.media_type,
            "value": self.value,
        }


@dataclass(frozen=True)
class ExecRuntime:
    name: str = "python"
    version: str = field(default_factory=lambda: platform.python_version())
    dependencies_digest: str = "sha256:unspecified"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "dependencies_digest": self.dependencies_digest,
        }


@dataclass(frozen=True)
class ExecClaim:
    claim_space: str
    subject: str
    expression: Dict[str, Any]
    inputs: List[ExecInput]
    output: ExecOutput
    runtime: ExecRuntime = field(default_factory=ExecRuntime)
    schema_version: str = "0.1.0"
    kind: str = "exec_claim"

    @classmethod
    def inline(
        cls,
        claim_space: str,
        subject: str,
        code: str,
        inputs: List[ExecInput],
        output: ExecOutput,
        language: str = "python",
        runtime: Optional[ExecRuntime] = None,
    ) -> "ExecClaim":
        return cls(
            claim_space=claim_space,
            subject=subject,
            expression={
                "kind": "inline_expr",
                "language": language,
                "code": code.replace("'", "\\u0027"),
                "source_digest": sha256_text(code),
            },
            inputs=inputs,
            output=output,
            runtime=runtime or ExecRuntime(name=language),
        )

    @classmethod
    def source_ref(
        cls,
        claim_space: str,
        subject: str,
        entrypoint: str,
        source_digest: str,
        inputs: List[ExecInput],
        output: ExecOutput,
        language: str = "python",
        runtime: Optional[ExecRuntime] = None,
    ) -> "ExecClaim":
        return cls(
            claim_space=claim_space,
            subject=subject,
            expression={
                "kind": "source_ref",
                "language": language,
                "entrypoint": entrypoint,
                "source_digest": source_digest,
            },
            inputs=inputs,
            output=output,
            runtime=runtime or ExecRuntime(name=language),
        )

    @classmethod
    def fard_program(
        cls,
        claim_space: str,
        subject: str,
        program_digest: str,
        inputs: List[ExecInput],
        output: ExecOutput,
        entrypoint: str = "main",
        runtime: Optional[ExecRuntime] = None,
    ) -> "ExecClaim":
        return cls(
            claim_space=claim_space,
            subject=subject,
            expression={
                "kind": "fard_program",
                "language": "fard",
                "entrypoint": entrypoint,
                "program_digest": program_digest,
            },
            inputs=inputs,
            output=output,
            runtime=runtime or ExecRuntime(name="fard"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "claim_space": self.claim_space,
            "subject": self.subject,
            "expression": self.expression,
            "inputs": [x.to_dict() for x in self.inputs],
            "output": self.output.to_dict(),
            "runtime": self.runtime.to_dict(),
        }

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())

    def digest(self) -> str:
        return sha256_text(self.canonical_json())

    def to_publish_args(self, timestamp_unix_secs: int = 0) -> Dict[str, Any]:
        return {
            "claim_space": self.claim_space,
            "subject": self.subject,
            "predicate": "exec_claim",
            "object": self.to_dict(),
            "evidence_refs": [x.digest for x in self.inputs],
            "timestamp_unix_secs": timestamp_unix_secs,
        }
