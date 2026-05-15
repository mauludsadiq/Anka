import json
from pathlib import Path

from anka import ExecClaim, ExecInput, ExecOutput, ExecRuntime, value_digest


def load_schema():
    return json.loads(Path("schema/exec_claim_v0_1_0.json").read_text())


def assert_digest(s):
    assert isinstance(s, str)
    assert s.startswith("sha256:")
    assert len(s) == 71


def sample_input():
    return ExecInput(name="test_set", digest=value_digest({"x": [1, 2, 3]}))


def test_inline_expr_schema_shape():
    claim = ExecClaim.inline(
        claim_space="fard.execution.receipts",
        subject="sum_demo",
        code='sum(test_set["x"])',
        inputs=[sample_input()],
        output=ExecOutput(value=6),
    )
    d = claim.to_dict()
    assert d["kind"] == "exec_claim"
    assert d["schema_version"] == "0.1.0"
    assert d["expression"]["kind"] == "inline_expr"
    assert d["expression"]["language"] == "python"
    assert_digest(d["expression"]["source_digest"])
    assert_digest(d["output"]["digest"])
    assert d["runtime"]["dependencies_digest"] == "sha256:unspecified"


def test_source_ref_schema_shape():
    source_digest = value_digest({"file": "eval.py", "content": "def evaluate(): return 6"})
    claim = ExecClaim.source_ref(
        claim_space="fard.execution.receipts",
        subject="source_demo",
        entrypoint="model.evaluate",
        source_digest=source_digest,
        inputs=[sample_input()],
        output=ExecOutput(value=6),
    )
    d = claim.to_dict()
    assert d["expression"]["kind"] == "source_ref"
    assert d["expression"]["entrypoint"] == "model.evaluate"
    assert d["expression"]["source_digest"] == source_digest


def test_fard_program_schema_shape():
    program_digest = value_digest({"program": "main.fard"})
    claim = ExecClaim.fard_program(
        claim_space="fard.execution.receipts",
        subject="fard_demo",
        program_digest=program_digest,
        inputs=[sample_input()],
        output=ExecOutput(value=6),
    )
    d = claim.to_dict()
    assert d["expression"]["kind"] == "fard_program"
    assert d["expression"]["language"] == "fard"
    assert d["expression"]["program_digest"] == program_digest


def test_digest_is_deterministic():
    a = ExecClaim.inline(
        claim_space="fard.execution.receipts",
        subject="sum_demo",
        code='sum(test_set["x"])',
        inputs=[sample_input()],
        output=ExecOutput(value=6),
    )
    b = ExecClaim.inline(
        claim_space="fard.execution.receipts",
        subject="sum_demo",
        code='sum(test_set["x"])',
        inputs=[sample_input()],
        output=ExecOutput(value=6),
    )
    assert a.digest() == b.digest()
    assert a.canonical_json() == b.canonical_json()


def test_runtime_dependencies_digest_can_be_pinned():
    deps_digest = value_digest({"requirements": ["numpy==2.0.0"]})
    claim = ExecClaim.inline(
        claim_space="fard.execution.receipts",
        subject="sum_demo",
        code='sum(test_set["x"])',
        inputs=[sample_input()],
        output=ExecOutput(value=6),
        runtime=ExecRuntime(name="python", version="3.11", dependencies_digest=deps_digest),
    )
    assert claim.to_dict()["runtime"]["dependencies_digest"] == deps_digest


def test_schema_file_loads():
    schema = load_schema()
    assert schema["title"] == "ANKA ExecClaim v0.1.0"
    assert "inline_expr" in schema["$defs"]
    assert "source_ref" in schema["$defs"]
    assert "fard_program" in schema["$defs"]
