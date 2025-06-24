"""Silhouette command line interface."""

from pathlib import Path
from datetime import datetime
import subprocess
import os
import argparse
from silhouette_core.offline_mode import is_offline
from silhouette_core.dsl_parser import parse_dsl_file
from silhouette_core.module_loader import discover_modules
from silhouette_core.response_engine import get_response

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
        f"silhouette_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    with open(log_file, "a") as log:
        print("\n🟣 Silhouette CLI – Alignment Mode\nType 'exit' to quit.\n")
        display_alignment(alignment)
        display_modules(modules)

        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                response = "Silhouette: Purpose acknowledged. Session closed."
                print(response)
                log.write(f"You: {user_input}\n{response}\n")
                break

            if user_input.strip() == ":replay":
                from silhouette_core.replay_log_to_memory import parse_session_logs
                count = parse_session_logs(Path("logs"), Path("memory.jsonl"))
                print(f"Replayed {count} entries")
                log.write(f"You: {user_input}\nSilhouette: replayed {count} entries.\n")
                continue

            if user_input.strip() == ":selfcheck":
                from silhouette_core.selfcheck_engine import main as run_selfcheck
                run_selfcheck()
                log.write(f"You: {user_input}\nSilhouette: selfcheck run.\n")
                continue

            if user_input.strip() == ":backup":
                from silhouette_core.export import main as export_main
                export_main()
                log.write(f"You: {user_input}\nSilhouette: backup complete.\n")
                continue

            if user_input.strip() == ":reload":
                alignment = load_alignment()
                modules, module_funcs = load_modules()
                print("🔄 Alignment and modules reloaded.")
                display_alignment(alignment)
                display_modules(modules)
                log.write(f"You: {user_input}\nSilhouette: reloaded configuration.\n")
                continue

            if user_input.strip() == ":modules":
                display_modules(modules)
                log.write(f"You: {user_input}\nSilhouette: listed modules.\n")
                continue

            if user_input.strip() == ":export":
                print("📦 Exporting system state...")
                subprocess.run(["python", "-m", "silhouette_core.export"])
                log.write(f"You: {user_input}\nSilhouette: system state exported.\n")
                continue

            if user_input.startswith(":summarize"):
                from silhouette_core.graph_engine import build_graph, summarize_thread
                memory_path = "logs/memory.jsonl"
                graph = build_graph(memory_path)
                last_id = list(graph)[-1]
                summary = summarize_thread(last_id, graph)
                print(f"🧠 Summary: {summary}")
                log.write(f"You: {user_input}\nSilhouette: summarized thread.\n")

            elif user_input.startswith(":related"):
                from silhouette_core.embedding_engine import query_knowledge
                prompt = user_input[len(":related"):].strip()
                results = query_knowledge(prompt=prompt)
                print("🔍 Related:")
                for r in results:
                    print(f"[{r['score']}] {r['content']}")
                log.write(f"You: {user_input}\nSilhouette: related entries returned.\n")

            elif user_input.startswith(":search"):
                prompt = user_input[len(":search"):].strip()
                if not prompt:
                    print("Please provide a search query.")
                    continue
                from silhouette_core.embedding_engine import query_knowledge
                results = query_knowledge(prompt=prompt)
                for r in results:
                    print(f"[{r['score']}] {r['content']}")
                log.write(f"You: {user_input}\nSilhouette: search returned {len(results)} results.\n")

            elif user_input.strip() == ":restore":
                print("🗃 Restoring system state...")
                zip_path = input("Enter path to backup ZIP: ").strip()
                key_path = input("Enter path to key file: ").strip()
                subprocess.run([
                    "python",
                    "-m",
                    "silhouette_core.restore",
                    "--zip",
                    zip_path,
                    "--key",
                    key_path,
                ])
                log.write(f"You: {user_input}\nSilhouette: system state restored.\n")
                continue

            if user_input.startswith("calculate") and "Math" in module_funcs:
                result = module_funcs["Math"](user_input)
                response = f"Silhouette: {result}"
            else:
                response = get_response(user_input, alignment)

            print(response)
            log.write(f"You: {user_input}\n{response}\n")


def main():
    parser = argparse.ArgumentParser(description="Silhouette CLI")
    parser.add_argument("--no-repl", action="store_true", help="Exit without starting REPL")
    args = parser.parse_args()

    if is_offline():

        print("[SAFE MODE] Offline detected")

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