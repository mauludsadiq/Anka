from anka import AnkaClient, ExecClaim, ExecInput, ExecOutput, value_digest

alice = AnkaClient("http://localhost:18080")

dataset = {"x": [1, 2, 3]}
claim = ExecClaim.inline(
    claim_space="fard.execution.receipts",
    subject="sum_demo",
    code='sum(test_set["x"])',
    inputs=[ExecInput(name="test_set", digest=value_digest(dataset))],
    output=ExecOutput(value=6),
)

published = alice.publish_exec_claim(claim, timestamp_unix_secs=1775711001)
digest = published["digest_hex"]

fetched = alice.fetch_claim(digest)
envelope = fetched["envelope"]

print("published_ok:", published["ok"])
print("digest:", digest)
print("fetched_ok:", fetched["ok"])
print("claim_space:", envelope["claim"]["claim_space"])
print("predicate:", envelope["claim"]["predicate"])
print("subject:", envelope["claim"]["subject"])
