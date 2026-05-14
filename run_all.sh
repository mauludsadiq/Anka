#!/usr/bin/env bash
set -euo pipefail
fardrun test --program anka/tests/test_anka_layer1.fard
fardrun run --program anka/src/demo.fard --out out/demo
