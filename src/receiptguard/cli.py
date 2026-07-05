"""ReceiptGuard CLI.

  receiptguard run [scenario]      run a scenario, show baseline vs guarded
  receiptguard bench [n]           run the adversarial detection benchmark
  receiptguard serve [host] [port] launch the FastAPI demo server
  receiptguard verify-ledger PATH  replay + verify a SQLite audit chain
"""
from __future__ import annotations

import sys

from .config import settings


def _run(argv: list[str]) -> int:
    from .pipeline import ReceiptGuard

    adversarial = "--adversarial" in argv
    pos = [a for a in argv if not a.startswith("--")]
    scenario = pos[0] if pos else "refund_damaged"
    r = ReceiptGuard().run(scenario, adversarial=adversarial).to_dict()
    print(f"mode: {'MOCK' if r['mock'] else 'LIVE'}   scenario: {r['scenario']}\n")
    print("BASELINE (unguarded) — would ship:")
    print("  " + r["baseline"]["draft"])
    print(f"  -> {r['baseline']['failed']} fabricated claim(s)\n")
    print("RECEIPTGUARD — verified output:")
    print("  " + r["guarded"]["final_draft"])
    print(f"  -> shipped={r['guarded']['shipped']}  grounding={r['guarded']['score']}")
    print(f"\n  signed receipts: {', '.join(x['tool'] for x in r['receipts'])}")
    print(f"  audit chain: {'VERIFIED' if r['chain_ok'] else 'BROKEN'} ({len(r['audit'])} entries)")
    return 0


def _bench(argv: list[str]) -> int:
    sys.argv = ["benchmark", *(argv or [])]
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))
    import benchmark  # type: ignore
    benchmark.main()
    return 0


def _serve(argv: list[str]) -> int:
    import uvicorn
    host = argv[0] if argv else "0.0.0.0"
    port = int(argv[1]) if len(argv) > 1 else 8000
    print(f"ReceiptGuard demo on http://{host}:{port}  (mock={settings.mock})")
    uvicorn.run("receiptguard.api.app:app", host=host, port=port)
    return 0


def _verify_ledger(argv: list[str]) -> int:
    from .audit import AuditLedger

    if not argv:
        print("usage: receiptguard verify-ledger PATH"); return 2
    led = AuditLedger(argv[0])
    ok, idx = led.verify_chain()
    n = len(led.all())
    print(f"ledger: {argv[0]}  entries: {n}")
    print("chain: VERIFIED ✓" if ok else f"chain: BROKEN ✗ at entry {idx}")
    return 0 if ok else 1


def main() -> None:
    cmds = {"run": _run, "bench": _bench, "serve": _serve, "verify-ledger": _verify_ledger}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__); sys.exit(0)
    sys.exit(cmds[sys.argv[1]](sys.argv[2:]))


if __name__ == "__main__":
    main()
