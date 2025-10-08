#!/usr/bin/env bash
set -euo pipefail

src="examples/engine"
dst="static/examples/engine"
mkdir -p "$dst"
cp -u "$src"/*.yaml "$dst"/ 2>/dev/null || true
