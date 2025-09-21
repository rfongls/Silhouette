# Acceptance Checklist

## Interop UI
- [ ] Pipeline card click collapses other panels and expands target
- [ ] De‑ID → Validate transfers exact text
- [ ] Trays hidden until panel has output

## Logging
- [ ] Each step writes a task with correct `run_id` and monotonic `task_seq`
- [ ] Validate writes `details_json` with error counts/profile
- [ ] MLLP send row, ACK update on receipt

## Reports
- [ ] /reports/validate loads summary + search
- [ ] /reports/acks filters by ack_code/status/control_id/window
- [ ] Validate “Print report” renders metadata + results
