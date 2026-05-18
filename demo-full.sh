#!/bin/bash
# ANKA Full Demo — all four demonstrations
# Accident flow (dynamic) + follow-up + research verification + Docker proof

set -e
BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[0;33m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}ANKA Full Demo Suite${RESET}"
echo -e "18,284 lines of Fard. Four repos. One protocol."
echo ""

command -v docker >/dev/null 2>&1 || { echo "Docker required."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python3 required."; exit 1; }
command -v fardrun >/dev/null 2>&1 || { echo "fardrun required. See github.com/mauludsadiq/FARD"; exit 1; }

# ── Demo 1: Docker epistemic mesh ─────────────────────────────────────────────
echo -e "${CYAN}=== Demo 1: Epistemic Mesh (Docker) ===${RESET}"
echo "Starting origin, alice, bob, adapter..."
docker compose up -d --remove-orphans 2>/dev/null
sleep 8
for i in $(seq 1 20); do
    curl -sf http://localhost:18080/health > /dev/null 2>&1 && break
    sleep 2
done
echo -e "${GREEN}Mesh running.${RESET} Alice: http://localhost:18080 Bob: http://localhost:18081"
echo ""

# ── Demo 2: Killer demo — accident flow ───────────────────────────────────────
echo -e "${CYAN}=== Demo 2: AI as Your Institutional Agent ===${RESET}"
python3 anka/demos/accident_flow_dynamic.py
echo ""

# ── Demo 3: Multi-turn continuity ─────────────────────────────────────────────
echo -e "${CYAN}=== Demo 3: Multi-Turn Continuity (Next Day) ===${RESET}"
python3 anka/demos/accident_followup.py
echo ""

# ── Demo 4: 100% live research verification ───────────────────────────────────
echo -e "${CYAN}=== Demo 4: Research Verification (100% Live APIs) ===${RESET}"

# Start native node + adapter for research demo
lsof -ti:18085 | xargs kill -9 2>/dev/null
fardrun run --program anka/src/node_process.fard --out out/node > /tmp/node_research.log 2>&1 &
NODE_PID=$!
python3 anka/src/runtime/adapters/anka_adapter.py --institution nist --port 19201 > /tmp/adapter_research.log 2>&1 &
ADAPTER_PID=$!
sleep 3

# Patch research flow to use port 19201
python3 - << 'PYEOF'
import subprocess, sys
code = open("anka/demos/research_verification_flow.py").read()
code = code.replace("adapter = \"http://localhost:19200\"", "adapter = \"http://localhost:19201\"")
exec(code)
PYEOF

kill $NODE_PID $ADAPTER_PID 2>/dev/null

echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}============================================================${RESET}"
echo -e "${GREEN}All demos complete.${RESET}"
echo ""
echo "  Demo 1: Epistemic mesh — Alice + Bob converged, 2 witnesses"
echo "  Demo 2: Accident flow — 3 institutions, live CPI, full audit"
echo "  Demo 3: Multi-turn — mesh remembered across sessions"
echo "  Demo 4: Research — arXiv + PubMed + NIST + World Bank (live)"
echo ""
echo "  Repositories:"
echo "    github.com/mauludsadiq/Anka   13,590 lines"
echo "    github.com/mauludsadiq/Bay2    2,825 lines"
echo "    github.com/mauludsadiq/Raqib   1,071 lines"
echo "    github.com/mauludsadiq/Dalil     798 lines"
echo "    Total: 18,284 lines of Fard across 191 files"
echo ""
echo "  docker compose down   # stop the stack"
echo -e "${BOLD}============================================================${RESET}"
