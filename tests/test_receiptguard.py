"""Core invariants. Run: PYTHONPATH=src python3 -m pytest  (or python3 tests/test_receiptguard.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from receiptguard.audit import AuditLedger
from receiptguard.claims import Claim
from receiptguard.gateway import ToolGateway, TOOLS
from receiptguard.gateway.receipts import sign
from receiptguard.pipeline import ReceiptGuard
from receiptguard.verify import cross_check


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


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")
