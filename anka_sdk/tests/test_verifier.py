from anka import (
    ExecClaim,
    ExecInput,
    ExecOutput,
    value_digest,
    verify_exec_claim,
    verify_inline_expr,
    runtime_digest,
)


def sample_claim(output=6):
    dataset = {"x": [1, 2, 3]}
    return ExecClaim.inline(
        claim_space="fard.execution.receipts",
        subject="sum_demo",
        code="sum([1, 2, 3])",
        inputs=[ExecInput(name="test_set", digest=value_digest(dataset))],
        output=ExecOutput(value=output),
    )


def test_runtime_digest_is_stable_shape():
    d = runtime_digest()
    assert d.startswith("sha256:")
    assert len(d) == 71


def test_verify_inline_expr_succeeds_when_output_matches():
    result = verify_inline_expr(sample_claim(output=6))
    assert result.ok is True
    assert result.deterministic is True
    assert result.expected_output_digest == result.observed_output_digest
    assert result.receipt_digest.startswith("sha256:")


def test_verify_inline_expr_fails_when_output_differs():
    result = verify_inline_expr(sample_claim(output=7))
    assert result.ok is False
    assert result.expected_output_digest != result.observed_output_digest


def test_verify_exec_claim_dispatches_inline_expr():
    result = verify_exec_claim(sample_claim(output=6))
    assert result.ok is True
    assert result.verifier_version == "0.1.0"


def test_verification_result_is_serializable():
    result = verify_exec_claim(sample_claim(output=6)).to_dict()
    assert result["ok"] is True
    assert result["receipt_digest"].startswith("sha256:")
    assert "execution_time_ms" in result
