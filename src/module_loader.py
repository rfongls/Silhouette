
# silhouette_core_modules/module_loader.py

import os
import json
from pathlib import Path

MODULES_DIR = Path("modules")

class Module:
    def __init__(self, name, description, entrypoint):
        self.name = name
        self.description = description
        self.entrypoint = entrypoint

    def load(self):
        try:
            module_func = __import__(self.entrypoint, fromlist=['main']).main
            return module_func
        except Exception as e:
            print(f"Failed to load {self.name}: {e}")
            return None


def discover_modules():
    modules = []
    if not MODULES_DIR.exists():
        return modules

    for file in MODULES_DIR.glob("*.json"):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                module = Module(
                    name=data['name'],
                    description=data['description'],
                    entrypoint=data['entrypoint']
                )
                modules.append(module)
        except Exception as e:
            print(f"Error loading module from {file.name}: {e}")

    return modules
