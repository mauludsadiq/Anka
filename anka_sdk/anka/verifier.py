from __future__ import annotations

import contextlib
import hashlib
import io
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .exec_claim import ExecClaim, canonical_json, sha256_text, value_digest


VERIFIER_VERSION = "0.1.0"


def runtime_digest() -> str:
    payload = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
    }
    return value_digest(payload)


def stdout_digest(stdout: str, stderr: str) -> str:
    return sha256_text(
        canonical_json(
            {
                "stdout": stdout,
                "stderr": stderr,
            }
        )
    )


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    deterministic: bool
    expected_output_digest: str
    observed_output_digest: str
    runtime_digest: str
    execution_time_ms: int
    verifier_version: str
    receipt_digest: str
    stdout_digest: str
    stdout: str
    stderr: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "deterministic": self.deterministic,
            "expected_output_digest": self.expected_output_digest,
            "observed_output_digest": self.observed_output_digest,
            "runtime_digest": self.runtime_digest,
            "execution_time_ms": self.execution_time_ms,
            "verifier_version": self.verifier_version,
            "receipt_digest": self.receipt_digest,
            "stdout_digest": self.stdout_digest,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def _build_input_scope(exec_claim: ExecClaim) -> Dict[str, Any]:
    scope = {}
    for inp in exec_claim.inputs:
        scope[inp.name] = inp.digest
    return scope


def verify_inline_expr(exec_claim: ExecClaim) -> VerificationResult:
    expr = exec_claim.expression

    scope = _build_input_scope(exec_claim)

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    start = time.time()

    observed = None

    with contextlib.redirect_stdout(stdout_buffer):
        with contextlib.redirect_stderr(stderr_buffer):
            observed = eval(expr["code"], {}, scope)

    elapsed_ms = int((time.time() - start) * 1000)

    observed_digest = value_digest(observed)
    expected_digest = exec_claim.output.to_dict()["digest"]

    out = stdout_buffer.getvalue()
    err = stderr_buffer.getvalue()

    out_digest = stdout_digest(out, err)

    receipt = {
        "claim_digest": exec_claim.digest(),
        "expected_output_digest": expected_digest,
        "observed_output_digest": observed_digest,
        "runtime_digest": runtime_digest(),
        "stdout_digest": out_digest,
        "verifier_version": VERIFIER_VERSION,
    }

    receipt_digest = value_digest(receipt)

    return VerificationResult(
        ok=observed_digest == expected_digest,
        deterministic=True,
        expected_output_digest=expected_digest,
        observed_output_digest=observed_digest,
        runtime_digest=runtime_digest(),
        execution_time_ms=elapsed_ms,
        verifier_version=VERIFIER_VERSION,
        receipt_digest=receipt_digest,
        stdout_digest=out_digest,
        stdout=out,
        stderr=err,
    )


def verify_source_ref(exec_claim: ExecClaim) -> VerificationResult:
    raise NotImplementedError("source_ref verification not implemented yet")


def verify_fard_program(exec_claim: ExecClaim) -> VerificationResult:
    raise NotImplementedError("fard_program verification not implemented yet")


def verify_exec_claim(exec_claim: ExecClaim) -> VerificationResult:
    kind = exec_claim.expression["kind"]

    if kind == "inline_expr":
        return verify_inline_expr(exec_claim)

    if kind == "source_ref":
        return verify_source_ref(exec_claim)

    if kind == "fard_program":
        return verify_fard_program(exec_claim)

    raise ValueError(f"unknown expression kind: {kind}")
