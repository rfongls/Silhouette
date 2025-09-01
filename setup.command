#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 ./setup.py
read -n 1 -s -r -p "Press any key to close…"
