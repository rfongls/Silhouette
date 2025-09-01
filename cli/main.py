"""Silhouette command line interface."""

import argparse
import builtins
import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from silhouette_core.offline_mode import is_offline
from silhouette_core.dsl_parser import parse_dsl_file
from silhouette_core.module_loader import discover_modules
from silhouette_core.agent_loop import Agent
from agent_controller import (
    export_agent,
    fork_agent,
    import_agent,
    list_agents,
    merge_agents,
    spawn_agent,
)
from persona_diff import diff_with_base

# Instantiate agent after imports
agent = Agent()

# Global safe print to handle Unicode on all platforms
_orig_print = builtins.print


def print(*args, **kwargs):
    try:
        _orig_print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode("ascii", "ignore").decode("ascii"))
            else:
                safe_args.append(arg)
        _orig_print(*safe_args, **kwargs)

DSL_PATH = Path("docs/alignment_kernel/values.dsl")
LOG_DIR = Path("logs")


def load_alignment() -> dict:
    """Load alignment values from the DSL file."""
    return parse_dsl_file(DSL_PATH)


def load_modules():
    """Discover modules and load their entrypoints."""
    mods = discover_modules()
    functions = {}
    for m in mods:
        func = m.load()
        if func:
            functions[m.name] = func
    return mods, functions


def display_alignment(alignment: dict):
    """Pretty print loaded alignment sections."""
    print("\nLoaded Alignment Values:")
    for section, items in alignment.items():
        print(f"[{section}]")
        for k, v in items.items():
            print(f"  {k}: {v}")
    print()


def display_modules(modules):
    """Display discovered modules."""
    if not modules:
        print("No modules found.")
    else:
        print("Available Modules:")
        for m in modules:
            print(f"- {m.name}: {m.description}")
    print()


def launch_repl(alignment, modules, module_funcs):
    """Run REPL loop handling special commands and logging."""
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / (
        f"silhouette_session_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.txt"
    )

    # Ensure unicode characters are preserved regardless of system locale
    with open(log_file, "a", encoding="utf-8") as log:
        print("\n🟣 Silhouette CLI – Alignment Mode\nType 'exit' to quit.\n")
        display_alignment(alignment)
        display_modules(modules)

        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", ":exit", ":quit"]:
                response = "Silhouette: Purpose acknowledged. Session closed."
                print(response)
                log.write(f"You: {user_input}\n{response}\n")
                break

            cmd = user_input.strip()
            if cmd == ":replay":
                from silhouette_core.replay_log_to_memory import parse_session_logs
                count = parse_session_logs(Path("logs"), Path("memory.jsonl"))
                print(f"Replayed {count} entries")
                log.write(f"You: {user_input}\nSilhouette: replayed {count} entries.\n")
            elif cmd.startswith(":selfcheck"):
                args = cmd.split()[1:]
                from silhouette_core.selfcheck_engine import main as run_selfcheck
                run_selfcheck(args)
                log.write(f"You: {user_input}\nSilhouette: selfcheck run.\n")
            elif cmd == ":drift-report":
                from silhouette_core.drift_detector import main as drift_main
                drift_main([])
                log.write(f"You: {user_input}\nSilhouette: drift report generated.\n")
            elif cmd == ":summary":
                from silhouette_core.session_summarizer import main as summary_main
                summary_main([])
                log.write(f"You: {user_input}\nSilhouette: summary generated.\n")
            elif cmd == ":persona-audit":
                from silhouette_core.persona_audit import main as audit_main
                audit_main([])
                log.write(f"You: {user_input}\nSilhouette: persona audit run.\n")
            elif cmd == ":export-profile":
                from silhouette_core.profile_exporter import main as profile_main
                profile_main([])
                log.write(f"You: {user_input}\nSilhouette: profile exported.\n")
            elif cmd == ":backup":
                from silhouette_core.export import main as export_main
                export_main()
                log.write(f"You: {user_input}\nSilhouette: backup complete.\n")
            elif cmd == ":reload":
                alignment = load_alignment()
                modules, module_funcs = load_modules()
                print("🔄 Alignment and modules reloaded.")
                display_alignment(alignment)
                display_modules(modules)
                log.write(f"You: {user_input}\nSilhouette: reloaded configuration.\n")
            elif cmd == ":modules":
                display_modules(modules)
                log.write(f"You: {user_input}\nSilhouette: listed modules.\n")
            elif cmd == ":export":
                print("📦 Exporting system state...")
                subprocess.run(["python", "-m", "silhouette_core.export"])
                log.write(f"You: {user_input}\nSilhouette: system state exported.\n")
            elif cmd.startswith(":summarize"):
                from silhouette_core.graph_engine import build_graph, summarize_thread
                graph = build_graph("logs/memory.jsonl")
                last_id = list(graph)[-1]
                summary = summarize_thread(last_id, graph)
                print(f"🧠 Summary: {summary}")
                log.write(f"You: {user_input}\nSilhouette: summarized thread.\n")
            elif cmd.startswith(":related"):
                from silhouette_core.embedding_engine import query_knowledge
                prompt = cmd[len(":related"):].strip()
                results = query_knowledge(prompt=prompt)
                print("🔍 Related:")
                for r in results:
                    print(f"[{r['score']}] {r['content']}")
                log.write(f"You: {user_input}\nSilhouette: related entries returned.\n")
            elif cmd.startswith(":search"):
                prompt = cmd[len(":search"):].strip()
                if not prompt:
                    print("Please provide a search query.")
                    continue
                from silhouette_core.embedding_engine import query_knowledge
                results = query_knowledge(prompt=prompt)
                for r in results:
                    print(f"[{r['score']}] {r['content']}")
                log.write(f"You: {user_input}\nSilhouette: search returned {len(results)} results.\n")
            elif cmd == ":restore":
                print("🗃 Restoring system state...")
                zip_path = input("Enter path to backup ZIP: ").strip()
                key_path = input("Enter path to key file: ").strip()
                subprocess.run([
                    "python", "-m", "silhouette_core.restore",
                    "--zip", zip_path, "--key", key_path
                ])
                log.write(f"You: {user_input}\nSilhouette: system state restored.\n")
                continue

            elif user_input.startswith(":agent"):
                parts = user_input.split()
                if len(parts) < 2:
                    print("Usage: :agent <command>")
                    continue
                sub = parts[1]
                if sub == "spawn":
                    aid = spawn_agent()
                    print(f"Spawned agent {aid}")
                elif sub == "fork" and len(parts) >= 3:
                    aid = int(parts[2])
                    nid = fork_agent(aid)
                    print(f"Forked agent {aid} -> {nid}")
                elif sub == "merge" and len(parts) >= 4:
                    tgt = int(parts[2])
                    src = int(parts[3])
                    count = merge_agents(tgt, src)
                    print(f"Merged {count} entries from {src} into {tgt}")
                elif sub == "list":
                    print("Agents:", list_agents())
                elif sub == "export" and len(parts) >= 4:
                    aid = int(parts[2])
                    path = Path(parts[3])
                    export_agent(aid, path)
                    print(f"Exported {aid} to {path}")
                elif sub == "import" and len(parts) >= 4:
                    aid = int(parts[2])
                    path = Path(parts[3])
                    import_agent(aid, path)
                    print(f"Imported {path} into {aid}")
                elif sub == "deploy" and len(parts) >= 3:
                    target = parts[2]
                    from agent_controller import deploy_clone
                    archive = Path("silhouette_clone_v1.zip")
                    if not archive.exists():
                        print("Clone archive silhouette_clone_v1.zip not found")
                    else:
                        deploy_clone(archive, target)
                        print(f"Deployed clone to {target}")
                elif sub == "audit" and len(parts) >= 3:
                    aid = int(parts[2])
                    diff = diff_with_base(aid)
                    for line in diff:
                        print(line)
                    from silhouette_core.selfcheck_engine import main as run_selfcheck
                    run_selfcheck()
                else:
                    print("Unknown agent command")
                log.write(f"You: {user_input}\nSilhouette: agent command executed.\n")
                continue

            if user_input.startswith("calculate") and "Math" in module_funcs:
                result = module_funcs["Math"](user_input)
                response = f"Silhouette: {result}"

            else:
                if user_input.startswith("calculate") and "Math" in module_funcs:
                    result = module_funcs["Math"](user_input)
                    response = f"Silhouette: {result}"
                else:
                    response = agent.loop(user_input)

                # --- Per-turn JSONL logging (local artifacts only) ---
                try:
                    os.makedirs("artifacts", exist_ok=True)
                    prompt_hash = hashlib.sha256(user_input.encode("utf-8")).hexdigest()[:12]
                    event = {
                        "ts": time.time(),
                        "type": "turn",
                        "prompt_hash": prompt_hash,
                        "len_prompt": len(user_input),
                        "len_answer": len(response),
                        "preview": user_input[:120],
                    }
                    with open("artifacts/session.log.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(event, ensure_ascii=False) + "\n")
                except Exception:
                    # Logging must never break the CLI
                    pass

                print(response)
                log.write(f"You: {user_input}\n{response}\n")


def main():
    parser = argparse.ArgumentParser(description="Silhouette CLI")
    parser.add_argument("--no-repl", action="store_true", help="Exit without starting REPL")
    args = parser.parse_args()

    if is_offline():
        print("[SAFE MODE] Offline detected: throttling modules, no network calls.")

    if args.no_repl:
        return

    if not DSL_PATH.exists():
        print("⚠️ Alignment file not found.")
        return

    align = load_alignment()
    mods, funcs = load_modules()
    launch_repl(align, mods, funcs)


if __name__ == "__main__":
    main()
