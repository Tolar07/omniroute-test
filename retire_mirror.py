#!/usr/bin/env python3
"""
Mirror retirement script - migrates unique files from deprecated mirror to canonical vault
"""

import os
import shutil
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PROJECT_DOCS = REPO_ROOT / 'olp_xdv_agent' / 'olp_xdv' / 'docs' / 'obsidian-vault'
# Deprecated mirror lives outside the repo. Override with RETIRED_VAULT_ROOT
# to point at wherever the retired vault sits on this machine.
VAULT_ROOT = Path(
    os.environ.get('RETIRED_VAULT_ROOT')
    or (Path.home() / 'Documents' / 'OLP_XDV_Vault')
)

SYNC_FILES = [
    'Agents.md',
    'Architecture.md',
    'Decisions Log.md',
    'OLP XDV.md',
    'Open Questions.md',
    'Protected Constants.md',
    'README.md',
    'Rules.md'
]

MIRROR_ONLY_FILES = [
    'API Keys.md',
    'OLP_XDV_Framework_Index.md',
    'Vault-Memory-Index.md'
]

CANONICAL_ONLY_FILES = [
    'Loops.md'
]

DEPRECATED_NOTICE = """# DEPRECATED MIRROR -- DO NOT EDIT

> **Architect Directive 2026-08-16:** The canonical vault is the git-tracked copy at:
> `olp_xdv_agent/olp_xdv/docs/obsidian-vault/`
>
> This folder (`Documents/OLP_XDV_Vault/`) is a **deprecated mirror** maintained for backward compatibility only.
> All edits must be made in the canonical vault. Changes here will be overwritten by the sync process.
>
> **Mirror retired:** 2026-08-18 (auto-migrated unique files to canonical vault)
>
> ---
>
> ### Migrated Files (now in canonical vault)
> - `Vault-Memory-Index.md` -> canonical vault (updated)
> - `OLP_XDV_Framework_Index.md` -> canonical vault (updated)
> - `API Keys.md` -> canonical vault (sanitized, credentials only in .env)
> - `Loops.md` -> already in canonical vault
>
> ### Files Remaining Here (read-only reference)
> - `Pipeline Runs/` -- historical pipeline artifacts
> - `.obsidian/` -- Obsidian workspace config
> - `.trash/` -- Obsidian trash
"""

def file_hash(filepath):
    try:
        content = filepath.read_text(encoding='utf-8')
        return hashlib.md5(content.encode()).hexdigest()[:8]
    except:
        return None

def sanitize_api_keys(content):
    import re
    content = re.sub(r'`[a-f0-9]{32}`', '`<REDACTED>`', content)
    content = re.sub(r'`[A-Za-z0-9_-]{20,}`', '`<REDACTED>`', content)
    content = re.sub(r'`\d{10}:[A-Za-z0-9_-]{35}`', '`<REDACTED>`', content)
    content = re.sub(r'`pplx-[A-Za-z0-9_-]{40,}`', '`<REDACTED>`', content)
    content = re.sub(r'`fc-[a-f0-9]{32}`', '`<REDACTED>`', content)
    content = re.sub(r'\| `.*?` \|', '| `<REDACTED>` |', content)
    return content

def check_status():
    print("=== Sync Status ===")
    print("\n--- Governance Files (bidirectional) ---")
    for f in SYNC_FILES:
        proj_path = PROJECT_DOCS / f
        vault_path = VAULT_ROOT / f
        proj_hash = file_hash(proj_path)
        vault_hash = file_hash(vault_path)

        if not proj_hash and not vault_hash:
            print(f"  {f}: MISSING BOTH")
        elif not proj_hash:
            print(f"  {f}: ONLY IN MIRROR ({vault_hash})")
        elif not vault_hash:
            print(f"  {f}: ONLY IN CANONICAL ({proj_hash})")
        elif proj_hash == vault_hash:
            print(f"  {f}: IN SYNC ({proj_hash})")
        else:
            print(f"  {f}: DIVERGED canonical={proj_hash} mirror={vault_hash}")

    print("\n--- Mirror-Only Files (to migrate on retire) ---")
    for f in MIRROR_ONLY_FILES:
        vault_path = VAULT_ROOT / f
        vault_hash = file_hash(vault_path)
        if vault_hash:
            print(f"  {f}: EXISTS in mirror ({vault_hash}) -- will migrate")
        else:
            print(f"  {f}: NOT FOUND in mirror")

    print("\n--- Canonical-Only Files ---")
    for f in CANONICAL_ONLY_FILES:
        proj_path = PROJECT_DOCS / f
        proj_hash = file_hash(proj_path)
        if proj_hash:
            print(f"  {f}: EXISTS in canonical ({proj_hash})")
        else:
            print(f"  {f}: NOT FOUND in canonical")

def retire_mirror(dry_run=True):
    print(f"=== Retire Mirror: Migrate unique files to Canonical {'(DRY-RUN)' if dry_run else ''} ===")

    if not PROJECT_DOCS.exists():
        print(f"[ERROR] Canonical vault not found: {PROJECT_DOCS}")
        return False
    if not VAULT_ROOT.exists():
        print(f"[ERROR] Mirror vault not found: {VAULT_ROOT}")
        return False

    migrated = 0
    failed = 0

    # 1. Migrate mirror-only files to canonical
    print('\n--- Migrating mirror-only files ---')
    for f in MIRROR_ONLY_FILES:
        src = VAULT_ROOT / f
        dst = PROJECT_DOCS / f
        if src.exists():
            content = src.read_text(encoding='utf-8')
            # For API Keys.md, sanitize credentials
            if f == 'API Keys.md':
                content = sanitize_api_keys(content)
                print(f"  [OK] {f} (sanitized)")
            else:
                print(f"  [OK] {f}")
            if not dry_run:
                dst.write_text(content, encoding='utf-8')
            migrated += 1
        else:
            print(f"  [WARN] {f}: Not found in mirror, skipping")

    # 2. Create DEPRECATED_NOTICE.md in mirror root
    print('\n--- Marking mirror as deprecated ---')
    notice_path = VAULT_ROOT / 'DEPRECATED_NOTICE.md'
    if not dry_run:
        notice_path.write_text(DEPRECATED_NOTICE, encoding='utf-8')
    print(f"  [OK] DEPRECATED_NOTICE.md created in mirror root")

    # 3. Make mirror files read-only (Windows: attrib +R)
    if not dry_run:
        import subprocess
        try:
            subprocess.run(['attrib', '+R', '/S', '/D', str(VAULT_ROOT / '*.md')], shell=True)
            print(f"  [OK] Mirror .md files marked read-only")
        except Exception as e:
            print(f"  [WARN] Could not set read-only: {e}")
    else:
        print(f"  [DRY-RUN] Would mark mirror .md files read-only")

    print(f"\n=== Mirror Retirement {'(DRY-RUN)' if dry_run else ''} Complete ===")
    print(f"Migrated: {migrated} files")
    if failed > 0:
        print(f"Failed: {failed} files")
    print(f"\nNext steps:")
    print(f"  1. Verify canonical vault has all migrated files")
    print(f"  2. Remove mirror from additionalDirectories in settings.json")
    print(f"  3. Update Vault-Memory-Index.md in canonical to reflect new state")
    print(f"  4. Future: remove mirror folder entirely")

    return True

if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if mode == 'status':
        check_status()
    elif mode == 'retire-mirror':
        retire_mirror(dry_run)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)