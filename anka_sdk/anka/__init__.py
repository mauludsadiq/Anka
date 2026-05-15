"""
ANKA Python SDK
The interoperability substrate for AI-operated systems.
"""

from .client import AnkaClient
from .exceptions import AnkaError, AnkaConnectionError, AnkaHTTPError, AnkaRateLimitError, AnkaNotFoundError
from .exec_claim import ExecClaim, ExecInput, ExecOutput, ExecRuntime, canonical_json, sha256_text, value_digest
from .agent import publish_llm_output, AnkaAgent
from .verifier import VerificationResult, verify_exec_claim, verify_inline_expr, runtime_digest

__version__ = "0.1.0"

__all__ = [
    "AnkaClient",
    "AnkaError",
    "AnkaConnectionError",
    "AnkaHTTPError",
    "AnkaRateLimitError",
    "AnkaNotFoundError",
    "ExecClaim",
    "ExecInput",
    "ExecOutput",
    "ExecRuntime",
    "canonical_json",
    "sha256_text",
    "value_digest",
    "publish_llm_output",
    "AnkaAgent",
    "VerificationResult",
    "verify_exec_claim",
    "verify_inline_expr",
    "runtime_digest",
]
