# Roadmap

| PR   | Title                                              | Status     | Purpose                                                        |
| ---- | -------------------------------------------------- | ---------- | -------------------------------------------------------------- |
| 1–3  | Agent Hardening                                    | ✅ Done     | Safe calc, eval runner, deny patterns, logging                 |
| 4–5  | Data Prep + SFT                                    | ✅ Done     | Seed dataset, dry-run training                                 |
| 6–8  | KD Pipeline                                        | ✅ Done     | Teacher outputs, KD run, eval reporting                        |
| 9    | Quantization + Latency                             | ✅ Done     | INT8 + latency probe                                           |
| 10   | Profile + Self-check                               | ✅ Done     | Policy, deny rules, latency gates                              |
| 11   | Eval Suites                                        | ✅ Done     | Basic developer evals                                          |
| 11.2 | Runtime Compile/Run Evals                          | ✅ Done     | FastAPI, ML, multi-file                                        |
| 12   | Skill Registry + RAG-to-Skill                      | ✅ Done     | Dynamic skill ingestion                                        |
| 13   | Versioned Skills + Scoreboard                      | ✅ Done     | Skill@vN, scoreboard HTML                                      |
| 14   | Dataset Synthesis                                  | ✅ Done     | Runtime → KD traces                                            |
| 15   | Build Runner Archival + File-Fence Adapter         | ✅ Done     | Prompts, zips, training adapter                                |
| 15.2 | Phase Scoreboards                                  | ✅ Done     | Phase snapshots linked                                         |
| 16   | Scoreboard History                                 | ✅ Done     | history.html                                                   |
| 16.2 | Per-phase Summaries + Trends                       | ✅ Done     | ▲/▼ badges                                                     |
| 17   | Security & Compliance v1                           | ✅ Done     | Redaction, PII, secrets, deny rules                            |
| 18   | Containerized Runtime + Compliance v2 + Watermarks | ✅ Done     | Java/.NET/Android builds, SPDX, watermarking, license template |
| 19   | Cross-Language Runtime Reframe                     | ✅ Done     | Docs/CI clarity, Vision anchored                               |
| 20   | Web + Python Runtimes + Linters                    | 🔜 Planned | Expand eval coverage                                           |
| 21   | C++/CMake Runtimes                                 | 🔜 Planned | Add systems-level stack                                        |
| 22   | Data Flywheel v2                                   | 🔜 Planned | Curated trace promotion                                        |
| 23   | Regression Gates & Latency Targets                 | 🔜 Planned | CI thresholds per lane                                         |
| 24   | Packaging & CLI UX                                 | 🔜 Planned | pip package, CLI polish                                        |
| 25   | Edge Targets                                       | 🔜 Planned | GGUF/ONNX quantization                                         |
| 26   | Release Playbook & Artifacts                       | 🔜 Planned | RELEASE.md, artifact bundle                                    |
| 27   | License Ops                                        | 🔜 Planned | Customer license issuance & watermark embedding                |

