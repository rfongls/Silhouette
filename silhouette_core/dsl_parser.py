
from pathlib import Path

def parse_dsl_file(filepath):
    """
    Parses the alignment DSL file with sections and returns a nested dictionary.
    Supports sections like [values], [rules], [intents], [tone].
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(f"Alignment DSL not found at {filepath}")

    data = {}
    current_section = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                data[current_section] = {}
            elif "=" in line and current_section:
                key, val = [x.strip() for x in line.split("=", 1)]
                data[current_section][key] = val.strip('"')

    return data
