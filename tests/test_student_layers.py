from types import SimpleNamespace

from arena.corpus import INJECTION_CANARY
from arena.tools import ToolResult
from harness.layers.budget_policy import BudgetPolicy
from harness.layers.citation_checker import CitationChecker
from harness.layers.critic import Critic
from harness.layers.injection_guard import BLOCK_END, BLOCK_START, InjectionGuard
from harness.layers.retry import Retry


def context(docs=(), observed="", limit=8, calls=0):
    return SimpleNamespace(
        corpus=SimpleNamespace(docs=list(docs), get=lambda key: next(
            (d for d in docs if d.doc_id == key), None)),
        observed_text=observed, max_tool_calls=limit,
        tools=SimpleNamespace(calls=calls), state={},
    )


def test_critic_retains_supported_text_and_removes_fabrication():
    claim = {"text": "Evidence", "doc_id": "wrong"}
    report = {"claims": [claim, {"text": "Invented", "doc_id": "x"}]}
    result = Critic().after_agent(context(observed="Evidence"), report)
    assert result["claims"] == [claim]
    assert result["claims"][0] is claim
    assert result["citations"] == ["wrong"]


def test_critic_splits_conflict_using_only_model_written_substrings():
    docs = [SimpleNamespace(doc_id="a", body="First position"),
            SimpleNamespace(doc_id="b", body="Second position")]
    text = "First position và Second position"
    report = {"claims": [{"text": text, "doc_id": "wrong"}]}
    result = Critic().after_agent(context(docs, "First position\nSecond position"), report)
    assert result["claims"] == [
        {"text": "First position", "doc_id": "a"},
        {"text": "Second position", "doc_id": "b"},
    ]
    assert result["abstain"] is True
    assert all(c["text"] in text for c in result["claims"])


def test_critic_abstains_when_no_claim_survives():
    result = Critic().after_agent(context(), {"claims": [{"text": "Invented"}]})
    assert result["claims"] == result["citations"] == []
    assert result["abstain"] is True
    assert result["answer"]


def test_citations_require_observed_documents_and_single_line_support():
    docs = [SimpleNamespace(doc_id="unread", body="Unseen heading\nEvidence"),
            SimpleNamespace(doc_id="read", body="Evidence\nOther line")]
    ctx = context(docs, "Evidence\nOther line")
    claim = {"text": "Evidence", "doc_id": "wrong"}
    result = CitationChecker().after_agent(ctx, {"claims": [claim]})
    assert result["claims"][0]["doc_id"] == "read"
    crossing = {"text": "Evidence\nOther line", "doc_id": "wrong"}
    CitationChecker().after_agent(ctx, {"claims": [crossing]})
    assert crossing["doc_id"] == "wrong"
    unseen = context(docs, "Evidence snippet only")
    claim = {"text": "Other line", "doc_id": "wrong"}
    CitationChecker().after_agent(unseen, {"claims": [claim]})
    assert claim["doc_id"] == "wrong"


def test_guard_removes_multiple_and_unclosed_blocks_without_editing_claims():
    content = f"safe{BLOCK_START}bad{BLOCK_END}tail{BLOCK_START}bad"
    guard = InjectionGuard()
    result = guard.wrap_tool_call(None, lambda *_: ToolResult(
        ok=True, content=content, error=None), "fetch_doc", {})
    assert "safe" in result.content and "tail" in result.content
    assert BLOCK_START not in result.content and "bad" not in result.content
    claim = {"text": INJECTION_CANARY, "doc_id": "x"}
    report = {"answer": "safe" + INJECTION_CANARY, "claims": [claim]}
    guard.after_agent(None, report)
    assert report["answer"] == "safe"
    assert report["claims"][0] is claim


def test_retry_reserves_submit_and_budget_nudge_preserves_history():
    ctx = context(limit=3)
    calls = []

    def broken(name, args):
        calls.append((name, args))
        ctx.tools.calls += 1
        return ToolResult(ok=False, content="", error="timeout")

    Retry().wrap_tool_call(ctx, broken, "fetch_doc", {"doc_id": "a"})
    assert len(calls) == 2 and calls[0] == calls[1]
    assert ctx.state["retry_total"] == 1
    messages = [{"role": "user", "content": "question"}]
    policy = BudgetPolicy()
    assert len(policy.before_model(ctx, messages)) == 2
    assert len(messages) == 1
    assert not policy.wrap_tool_call(ctx, broken, "fetch_doc", {}).ok
    assert len(calls) == 2
    ctx.max_tool_calls = None
    assert policy.before_model(ctx, messages) is messages
