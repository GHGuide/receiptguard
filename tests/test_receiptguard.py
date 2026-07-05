"""Core invariants. Run: PYTHONPATH=src python3 -m pytest  (or python3 tests/test_receiptguard.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from receiptguard.audit import AuditLedger
from receiptguard.claims import Claim
from receiptguard.gateway import ToolGateway, TOOLS
from receiptguard.gateway.receipts import sign
from receiptguard.pipeline import ReceiptGuard
from receiptguard.recovery import decide
from receiptguard.verify import cross_check, cross_check_all


def test_receipt_signature_unforgeable():
    gw = ToolGateway(TOOLS)
    gw.call("lookup_order", order_id="ORD-1001")
    r = gw.store.all()[0]
    assert gw.store.verify_signature(r)
    # tamper the output -> recomputed payload signature no longer matches the stored sig
    r.output_hash = "deadbeef"
    assert sign(r.signing_payload()) != r.sig


def test_detect_fabricated_tool_reference():
    gw = ToolGateway(TOOLS)
    gw.call("lookup_order", order_id="ORD-1001")  # inventory NOT called
    v = cross_check(Claim("Inventory shows 0 units in stock.", "tool_derived"), gw.store.all())
    assert v.status == "unbacked" and v.failed


def test_detect_value_mismatch():
    gw = ToolGateway(TOOLS)
    gw.call("check_inventory", item="Wireless Earbuds")  # real = 12 units
    v = cross_check(Claim("Inventory shows 0 units in stock.", "tool_derived"), gw.store.all())
    assert v.status == "contradicted" and v.failed


def test_detect_false_absence():
    gw = ToolGateway(TOOLS)
    gw.call("search_kb", query="return-policy")  # returns a non-empty result
    v = cross_check(Claim("No results were found for the return policy.", "absence"), gw.store.all())
    assert v.status == "false_absence" and v.failed


def test_backed_claim_passes():
    gw = ToolGateway(TOOLS)
    gw.call("check_inventory", item="Wireless Earbuds")
    v = cross_check(Claim("Inventory shows 12 units in stock.", "tool_derived"), gw.store.all())
    assert v.status == "backed" and not v.failed


def test_ledger_tamper_breaks_chain():
    led = AuditLedger(":memory:")
    led.append("a", {"x": 1}, ts=1.0)
    led.append("b", {"x": 2}, ts=2.0)
    led.append("c", {"x": 3}, ts=3.0)
    ok, idx = led.verify_chain()
    assert ok and idx == -1
    led.conn.execute("UPDATE entries SET payload=? WHERE idx=2", ('{"x": 999}',))
    led.conn.commit()
    ok, idx = led.verify_chain()
    assert not ok and idx == 2


def test_pipeline_blocks_then_ships_clean():
    r = ReceiptGuard().run("refund_damaged").to_dict()
    assert r["baseline"]["failed"] >= 1          # unguarded would ship fabrications
    assert r["guarded"]["shipped"] is True        # guarded converges
    assert r["guarded"]["score"] >= 0.85          # final output fully grounded
    assert r["chain_ok"] is True                   # audit chain intact
    final_verdicts = r["guarded"]["iterations"][-1]["verdicts"]
    assert all(v["status"] not in ("unbacked", "contradicted", "false_absence") for v in final_verdicts)


# ----------------------------- demo-safety / regression locks -----------------------------

def test_date_not_parsed_as_amount():
    """A date in a backed claim must not be misread as a numeric mismatch (demo-breaker)."""
    gw = ToolGateway(TOOLS)
    gw.call("check_inventory", item="Wireless Earbuds")  # real = 12
    v = cross_check(Claim("Inventory shows 12 units as of 2024-01-15.", "tool_derived"), gw.store.all())
    assert v.status == "backed" and not v.failed


def test_relative_numeric_tolerance():
    """$410 claim vs a 410.0 receipt matches; a true mismatch is still caught."""
    gw = ToolGateway(TOOLS)
    gw.call("process_refund", order_id="ORD-2002", amount=410.0)
    assert cross_check(Claim("I processed a $410 refund.", "tool_derived"), gw.store.all()).status == "backed"
    assert cross_check(Claim("I processed a $500 refund.", "tool_derived"), gw.store.all()).failed


def test_warranty_scenario_escalates_to_human():
    """2nd scenario: agent fabricates, then on replan grounds in receipts and ESCALATES
    (outside policy window) — Track-4 human-in-the-loop, all final claims backed."""
    r = ReceiptGuard().run("warranty_replacement").to_dict()
    assert r["baseline"]["failed"] >= 1
    assert r["guarded"]["shipped"] is True
    assert "escalat" in r["guarded"]["final_draft"].lower()
    final = r["guarded"]["iterations"][-1]["verdicts"]
    assert all(v["status"] not in ("unbacked", "contradicted", "false_absence") for v in final)


def test_budget_exhausted_forces_replan_not_proceed():
    bad = cross_check_all([Claim("I processed a $79 refund.", "tool_derived")], ToolGateway(TOOLS).store.all())
    d = decide(bad, iteration=2, max_iterations=3)  # last allowed iteration
    assert d.action == "replan" and d.failed  # never silently proceed with unbacked claims


def test_forged_receipt_rejected():
    """A receipt signed with the wrong secret fails verification (HMAC is load-bearing)."""
    gw = ToolGateway(TOOLS)
    gw.call("lookup_order", order_id="ORD-1001")
    r = gw.store.all()[0]
    r.sig = sign(r.signing_payload(), secret="attacker-secret")
    assert not gw.store.verify_signature(r)


def test_tool_failure_still_receipted():
    """A tool that raises still yields a signed error-receipt (invariant preserved)."""
    def boom(**_):
        raise RuntimeError("downstream 500")
    gw = ToolGateway({"boom": boom})
    out = gw.call("boom", x=1)
    assert out["error"] == "tool_execution_failed"
    assert len(gw.store.all()) == 1 and gw.store.verify_signature(gw.store.all()[0])


def test_adversarial_injection_is_caught_and_dropped():
    """Adversarial mode injects an unbacked claim; the guard must flag it in the
    baseline and ship a final output with the lie removed (the live-demo money-shot)."""
    r = ReceiptGuard().run("refund_damaged", adversarial=True).to_dict()
    assert "goodwill credit" in r["baseline"]["draft"].lower()
    assert any("goodwill" in v["text"].lower() and v["status"] in
               ("unbacked", "contradicted", "false_absence") for v in r["baseline"]["verdicts"])
    assert r["guarded"]["shipped"] is True
    assert "goodwill credit" not in r["guarded"]["final_draft"].lower()


def test_extraction_fails_safe_on_actions():
    """Mis-typing must be CONSERVATIVE: action/result claims type as tool_derived
    (verified), never downgraded to opinion/inference (which would skip verification)."""
    from receiptguard.claims import extract_claims
    for draft in ("I processed a $79 refund to the customer.",
                  "I shipped the replacement and sent the tracking number.",
                  "Inventory shows 12 units in stock."):
        claims = extract_claims(draft)
        assert claims and claims[0].type == "tool_derived", f"{draft!r} -> {claims}"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")
