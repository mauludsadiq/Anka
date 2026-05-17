#!/usr/bin/env python3
# anka/setup.py
# Run once before first boot to configure your node.
# Usage: python3 anka/setup.py --name "Oxford-Node" --institution "Oxford" \
#                              --address "http://oxford.example.com:18080" \
#                              --origin "http://origin.anka.network:18090" \
#                              --db out/node/anka_node.db

import argparse
import json
import os
import sqlite3
import hashlib

parser = argparse.ArgumentParser(description='Configure an ANKA node')
parser.add_argument('--name', required=True, help='Node name (e.g. Oxford-Climate-Node)')
parser.add_argument('--institution', required=True, help='Institution name (e.g. Oxford)')
parser.add_argument('--address', required=True, help='This node external address (e.g. http://oxford.example.com:18080)')
parser.add_argument('--origin', default='http://localhost:18090', help='Origin node address')
parser.add_argument('--peers', default='', help='Comma-separated initial peer addresses')
parser.add_argument('--db', default='out/node/anka_node.db', help='Path to node database')
args = parser.parse_args()

os.makedirs(os.path.dirname(args.db), exist_ok=True)

peers = [p.strip() for p in args.peers.split(',') if p.strip()]

config = {
    'node_name': args.name,
    'institution': args.institution,
    'local_address': args.address,
    'origin_address': args.origin,
    'peers': peers
}

# Generate deterministic keypair seed from operator config
# In production this would be a hardware-generated key
seed = f"anka-operator-{args.name}-{args.institution}-{args.address}"
seed_hash = hashlib.sha256(seed.encode()).hexdigest()

# Identity stored separately so it survives config updates
identity = {
    'node_name': args.name,
    'institution': args.institution,
    'local_address': args.address,
    'seed': seed,
    'seed_hash': seed_hash
}

conn = sqlite3.connect(args.db)
conn.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT)")
conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('node_config', ?)",
             (json.dumps(config),))
conn.commit()
conn.close()

print(f"Node configured:")
print(f"  name:        {args.name}")
print(f"  institution: {args.institution}")
print(f"  address:     {args.address}")
print(f"  origin:      {args.origin}")
print(f"  peers:       {peers}")
print(f"  db:          {args.db}")
print(f"")
print(f"Start the node:")
print(f"  fardrun run --program anka/src/node_process.fard --out out/node")
