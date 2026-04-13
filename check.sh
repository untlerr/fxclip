#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile fxclip_core.py
python3 fxclip_tests.py

echo "fxclip check: OK"
