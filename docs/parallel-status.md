# Parallel-lane status board

6 lanes hardening ReceiptGuard for submission. One lane owns each file-set; cross-file edits are REQUESTED here, never made directly.

## Lane ownership
| Lane | Branch | OWNS | Model |
|---|---|---|---|
| L1 core-verifier | lane/L1-core-verifier | `src/receiptguard/{verify,recovery,gateway,claims}/**`, `tests/test_receiptguard.py` | Opus high |
| L2 agent-api | lane/L2-agent-api | `src/receiptguard/{agent,pipeline,api,config,cli}.py`, `src/receiptguard/llm/**` | Opus med |
| L3 benchmark-eval | lane/L3-benchmark-eval | `eval/**`, `tests/test_bench_*.py` | Fable 5 med |
| L4 demo-ui | lane/L4-demo-ui | `static/**` | Fable 5 med |
| L5 mcp-deploy | lane/L5-mcp-deploy | `src/receiptguard/mcp/**`, `Dockerfile`, `s.yaml`, `docs/fc-deployment.md` | Opus med |
| L6 narrative | lane/L6-narrative | `README.md`, `docs/**` (excl fc-deployment.md, judge-council-report.md, parallel-status.md, LANES.md) | Fable 5 med |

## Contracts (shared files — request here, don't cross-edit)
- **README.md** → owned by **L6**. L3 (benchmark numbers), L4 (live-URL + screenshot block), L5 (ledger persistence note) POST a request below; L6 applies.
- **config.py** → owned by **L2**. L2 unifies the model name to `qwen3.7-max` everywhere in code.
- **llm/qwen.py** → owned by **L2** (needs the SSE reasoning stream). L5 does NOT touch `llm/`.

## Edit requests (append below; owning lane checks this file before finishing)
- (none yet)

## Lane status (each lane updates its row on start / done)
- L1: pending
- L2: pending
- L3: pending
- L4: pending
- L5: pending
- L6: pending
