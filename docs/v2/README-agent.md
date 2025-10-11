# Agent Landing & Orchestrator (Demo)

**Purpose:** Provide a landing page with a **Chat (beta)** box that can drive Engine features **without leaving the page**, and a live **Activity Timeline** that confirms what was added and when. No external LLM is used in this phase.

## Endpoints

- `POST /api/agent/interpret` → parse text to `{intent, params, steps}` (no side effects)  
- `POST /api/agent/execute` → run the steps; returns Execution Report + Activity id  
- `GET /api/agent/registry` → list supported intents and parameter schemas  
- `GET /api/agent/actions` → list recent actions  
- `GET /api/agent/actions/stream` → **SSE** stream of live actions

## Example commands

```
create inbound adt-in on 127.0.0.1:4321 for pipeline 3 allow 127.0.0.1/32
start endpoint adt-in
create outbound adt-out to 10.0.0.12:2575
send to adt-out: MSH|^~\&|SIL|CORE|TEST|SITE|202501011200||ADT^A01|0001|P|2.5\rPID|1||12345^^^SIL^MR\r
run pipeline 3 persist true
replay run 42 on pipeline 3
assist preview 3 lookback 14
generate 25 ADT messages to demo-adt
deidentify incoming/ward to ward_deid with pipeline 3
```

## Live confirmations

The landing page’s **Activity Timeline** uses SSE to show:

- Created inbound `adt-in` at `127.0.0.1:4321` (status: **running**)  
- Enqueued job #142 for pipeline #3  
- De-identified 128 files: **125 ok / 3 failed**, output → `data/agent/out/ward_deid`

Links to endpoint/job/run IDs make it easy to pivot to the manual Engine UI if needed.

## Demo folders

- `AGENT_DATA_ROOT` (default: `./data/agent`)  
  - **Input**: `AGENT_DATA_ROOT/in/<folder>/**/*.hl7`  
  - **Output**: `AGENT_DATA_ROOT/out/<folder>/*.hl7`

The orchestrator enforces confinement to this root.

## Notes

- Wildcard bind (`0.0.0.0`) is blocked unless `ENGINE_NET_BIND_ANY=1`.
- All actions are callable through the API for headless/demo scripting.
- In later phases, you can replace the deterministic parser with a real LLM.

## Phase 6B additions

- **Generate**  
  `generate 10 ADT messages to demo-adt` → writes `data/agent/out/demo-adt/gen_0001.hl7`…`gen_0010.hl7`

- **De-identify**  
  Place files in `data/agent/in/<your-folder>/**/*.hl7`, then run:  
  `deidentify <your-folder> to <your-folder>_deid with pipeline 3` → outputs appear in `data/agent/out/<your-folder>_deid/*.hl7`
