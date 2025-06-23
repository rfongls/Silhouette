
"""Silhouette command line interface."""

from pathlib import Path
from datetime import datetime

from dsl_parser import parse_dsl_file
from module_loader import discover_modules
from cli.response_engine import get_response


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

            if user_input.strip() == ":reload":
                alignment = load_alignment()
                modules, module_funcs = load_modules()
                print("🔄 Alignment and modules reloaded.")
                display_alignment(alignment)
                display_modules(modules)
                log.write(
                    f"You: {user_input}\nSilhouette: reloaded configuration.\n"
                )
                continue

            if user_input.strip() == ":modules":
                display_modules(modules)
                log.write(f"You: {user_input}\nSilhouette: listed modules.\n")
                continue

            if user_input.startswith("calculate") and "Math" in module_funcs:
                result = module_funcs["Math"](user_input)
                response = f"Silhouette: {result}"
            else:
                response = get_response(user_input, alignment)

            print(response)
            log.write(f"You: {user_input}\n{response}\n")


def main():
    if not DSL_PATH.exists():
        print("⚠️ Alignment file not found.")
        return
    align = load_alignment()
    mods, funcs = load_modules()
    launch_repl(align, mods, funcs)


if __name__ == "__main__":
    main()
