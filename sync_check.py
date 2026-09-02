#!/usr/bin/env python3
"""
Simple vault-memory sync check based on mappings
"""
import os
import json
import hashlib
from pathlib import Path

VAULT_ROOT = Path(r'c:/Users/Motunrayo/omniroute test/olp_xdv_agent/olp_xdv/docs/obsidian-vault')
MEMORY_ROOT = Path(r'c:/Users/Motunrayo/.claude/projects/C--Users-Motunrayo-omniroute-test/memory')
CONFIG_PATH = Path(r'c:/Users/Motunrayo/omniroute test/olp_xdv_agent/olp_xdv/.claude/config/vault-memory-mappings.json')

def get_file_hash(filepath):
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def main():
    print("=== Vault <-> Memory Sync Status ===")

    # Load mappings
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    mappings = config['FILE_MAPPINGS']

    diverged = 0
    missing_vault = 0
    missing_memory = 0
    in_sync = 0

    for mapping in mappings:
        vault_path = VAULT_ROOT / mapping['vault']
        memory_path = None
        if mapping.get('memory') and not mapping['memory'].endswith('/'):
            memory_path = MEMORY_ROOT / mapping['memory']

        vault_exists = vault_path.exists()
        memory_exists = memory_path is not None and memory_path.exists()

        if vault_exists and memory_exists:
            vault_hash = get_file_hash(vault_path)
            memory_hash = get_file_hash(memory_path)

            if vault_hash == memory_hash:
                print(f"   {mapping['vault']}: IN SYNC ({vault_hash[:8]}) [bidirectional]")
                in_sync += 1
            else:
                print(f"   {mapping['vault']}: DIVERGED (vault:{vault_hash[:8] if vault_hash else 'None'} memory:{memory_hash[:8] if memory_hash else 'None'})")
                diverged += 1
        elif vault_exists and not memory_exists:
            print(f"   {mapping['vault']}: ONLY IN VAULT [memory-to-vault-append]")
            missing_memory += 1
        elif not vault_exists and memory_exists:
            print(f"   {mapping['vault']}: ONLY IN MEMORY [vault-to-memory-append]")
            missing_vault += 1
        else:
            print(f"   {mapping['vault']}: MISSING IN BOTH")

    print(f"\nSummary: {in_sync} in sync, {diverged} diverged, {missing_vault} missing in vault, {missing_memory} missing in memory")

    if diverged == 0 and missing_vault == 0 and missing_memory == 0:
        print("✓ All files are in sync!")
        return 0
    else:
        print("✗ Sync issues detected")
        return 1

if __name__ == '__main__':
    exit(main())