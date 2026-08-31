#!/usr/bin/env node
/**
 * auto-sync-commit.js — Automated vault-memory sync + git commit
 * Run every 5 minutes via Windows Task Scheduler or cron
 *
 * Does:
 * 1. Vault <-> Memory bidirectional sync (HR54)
 * 2. Git add all changes
 * 3. Git commit if there are changes (sweeps other session's staged files)
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Resolve the repo root as the parent of this scripts/ directory so the same
// job runs on any checkout, on Windows or otherwise. Override with
// OMNIROUTE_REPO_ROOT when the script has to be invoked from elsewhere.
const REPO_ROOT = process.env.OMNIROUTE_REPO_ROOT || path.resolve(__dirname, '..');
const SYNC_SCRIPT = path.join(REPO_ROOT, 'olp_xdv_agent', 'olp_xdv', '.claude', 'scripts', 'hooks', 'vault-memory-sync.js');
const LOG_DIR = path.join(REPO_ROOT, 'logs', 'auto-sync');
const LOG_FILE = path.join(LOG_DIR, `auto-sync-${new Date().toISOString().split('T')[0]}.log`);

function ensureLogDir() {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
}

function log(msg) {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${msg}\n`;
  ensureLogDir();
  fs.appendFileSync(LOG_FILE, line, 'utf8');
  console.log(line.trim());
}

function runCmd(cmd, cwd = REPO_ROOT) {
  try {
    const output = execSync(cmd, { cwd, encoding: 'utf8', stdio: 'pipe' });
    return { success: true, output: output.trim() };
  } catch (e) {
    return { success: false, output: e.stdout?.toString() || e.message, error: e.stderr?.toString() };
  }
}

async function main() {
  log('═══════════════════════════════════════════════════════════');
  log('🔄 AUTO SYNC + COMMIT STARTED');
  log('═══════════════════════════════════════════════════════════');

  // 1. Run vault-memory sync (bidirectional)
  log('\n📦 Step 1: Vault <-> Memory sync (HR54)');
  const syncResult = runCmd(`node "${SYNC_SCRIPT}" reconcile`);
  if (syncResult.success) {
    log(`   ✅ Sync complete`);
    log(`   ${syncResult.output}`);
  } else {
    log(`   ⚠️  Sync had issues: ${syncResult.output}`);
    log(`   ${syncResult.error}`);
  }

  // 2. Check git status
  log('\n📋 Step 2: Git status check');
  const statusResult = runCmd('git status --short');
  if (statusResult.success) {
    const changes = statusResult.output.split('\n').filter(Boolean).length;
    log(`   Files changed: ${changes}`);
    if (changes > 0) {
      log(`   Changes:\n${statusResult.output.split('\n').map(l => '      ' + l).join('\n')}`);
    }
  }

  // 3. Git add all
  log('\n📥 Step 3: Git add -A (sweeps other session\'s staged files)');
  const addResult = runCmd('git add -A');
  if (addResult.success) {
    log('   ✅ Staged all changes');
  } else {
    log(`   ⚠️  Add failed: ${addResult.error}`);
  }

  // 4. Check if there's anything to commit
  log('\n💾 Step 4: Check for staged changes to commit');
  const diffResult = runCmd('git diff --cached --name-only');
  const stagedFiles = diffResult.success ? diffResult.output.split('\n').filter(Boolean) : [];

  if (stagedFiles.length > 0) {
    log(`   Staged files (${stagedFiles.length}): ${stagedFiles.join(', ')}`);

    // 5. Commit with descriptive message
    const timestamp = new Date().toISOString().replace('T', ' ').split('.')[0];
    const msg = `chore(auto): vault-memory sync + changes ${timestamp}\n\nAuto-sync: HR54 bidirectional vault<->memory sync\nStaged files: ${stagedFiles.length}\n\nCo-Authored-By: Claude <noreply@anthropic.com>`;

    log('\n✍️  Step 5: Committing changes');
    const commitResult = runCmd(`git commit -m "${msg}"`);
    if (commitResult.success) {
      log(`   ✅ Committed: ${commitResult.output.split('\n')[0]}`);
    } else {
      log(`   ⚠️  Commit failed: ${commitResult.error}`);
    }
  } else {
    log('   No staged changes to commit');
  }

  // 6. Final status
  log('\n📊 Step 6: Final status');
  const finalStatus = runCmd('git status --short');
  if (finalStatus.success) {
    log(`   Working tree: ${finalStatus.output.trim() ? 'DIRTY' : 'CLEAN'}`);
    if (finalStatus.output.trim()) {
      log(`   Remaining: ${finalStatus.output.trim()}`);
    }
  }

  log('\n═══════════════════════════════════════════════════════════');
  log('✅ AUTO SYNC + COMMIT COMPLETE');
  log('═══════════════════════════════════════════════════════════\n');
}

main().catch(err => {
  log(`\n❌ FATAL: ${err.message}`);
  process.exit(1);
});