/**
 * Vault-Memory Synchronization Script
 *
 * Bidirectional synchronization between the canonical vault (git-tracked)
 * and the agent memory system (persistent across sessions).
 *
 * Enforces HR54: Vault ↔ Memory sync required on SessionStart/SessionEnd
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const VAULT_ROOT = path.join(__dirname, '..', 'olp_xdv_agent', 'olp_xdv', 'docs', 'obsidian-vault');
const MEMORY_ROOT = path.join(__dirname, '..', '.claude', 'projects', 'c--Users-Motunrayo-omniroute-test', 'memory');
const LOG_FILE = path.join(MEMORY_ROOT, 'sync-log.md');

/**
 * Log synchronization activity
 * @param {string} message - Message to log
 */
function logSync(message) {
    const timestamp = new Date().toISOString();
    const logEntry = `- [${timestamp}] ${message}\n`;

    // Ensure log file exists
    if (!fs.existsSync(LOG_FILE)) {
        fs.writeFileSync(LOG_FILE, '# Vault-Memory Sync Log\n\n');
    }

    fs.appendFileSync(LOG_FILE, logEntry);
    console.log(`[SYNC] ${message}`);
}

/**
 * Get all markdown files in a directory (non-recursive)
 * @param {string} dir - Directory path
 * @returns {string[]} Array of file paths
 */
function getMarkdownFiles(dir) {
    try {
        const files = fs.readdirSync(dir);
        return files
            .filter(file => file.endsWith('.md'))
            .map(file => path.join(dir, file));
    } catch (error) {
        logSync(`Error reading directory ${dir}: ${error.message}`);
        return [];
    }
}

/**
 * Read file content
 * @param {string} filePath - Path to file
 * @returns {string|null} File content or null if error
 */
function readFile(filePath) {
    try {
        return fs.readFileSync(filePath, 'utf8');
    } catch (error) {
        logSync(`Error reading file ${filePath}: ${error.message}`);
        return null;
    }
}

/**
 * Write file content
 * @param {string} filePath - Path to file
 * @param {string} content - Content to write
 * @returns {boolean} True if successful
 */
function writeFile(filePath, content) {
    try {
        fs.writeFileSync(filePath, content, 'utf8');
        return true;
    } catch (error) {
        logSync(`Error writing file ${filePath}: ${error.message}`);
        return false;
    }
}

/**
 * Sync a single file from source to destination
 * @param {string} sourcePath - Source file path
 * @param {string} destPath - Destination file path
 * @param {string} direction - 'vault-to-memory' or 'memory-to-vault'
 * @returns {boolean} True if sync occurred
 */
function syncFile(sourcePath, destPath, direction) {
    const sourceContent = readFile(sourcePath);
    if (sourceContent === null) {
        return false;
    }

    const destContent = readFile(destPath);

    // If files are identical, no sync needed
    if (sourceContent === destContent) {
        return false;
    }

    // Determine which is newer based on modification time
    try {
        const sourceStat = fs.statSync(sourcePath);
        const destStat = fs.statSync(destPath);

        // If destination is newer, we might want to warn about potential conflict
        // For now, we'll use newest-wins strategy
        const sourceIsNewer = sourceStat.mtime > destStat.mtime;

        if (direction === 'vault-to-memory' || (direction === 'bidirectional' && sourceIsNewer)) {
            const success = writeFile(destPath, sourceContent);
            if (success) {
                logSync(`Synced ${path.basename(sourcePath)}: ${direction} (source newer)`);
                return true;
            }
        } else if (direction === 'memory-to-vault' || (direction === 'bidirectional' && !sourceIsNewer)) {
            const success = writeFile(sourcePath, destContent);
            if (success) {
                logSync(`Synced ${path.basename(sourcePath)}: ${direction} (dest newer or bidirectional)`);
                return true;
            }
        }
    } catch (error) {
        logSync(`Error checking file timestamps: ${error.message}`);
        // Fallback to direction-based sync
        if (direction === 'vault-to-memory' || direction === 'bidirectional') {
            const success = writeFile(destPath, sourceContent);
            if (success) {
                logSync(`Synced ${path.basename(sourcePath)}: ${direction} (fallback)`);
                return true;
            }
        }
    }

    return false;
}

/**
 * Synchronize vault to memory
 */
function syncVaultToMemory() {
    logSync('Starting vault → memory synchronization');

    const vaultFiles = getMarkdownFiles(VAULT_ROOT);
    let syncedCount = 0;

    for (const vaultFile of vaultFiles) {
        const relativePath = path.relative(VAULT_ROOT, vaultFile);
        const memoryFile = path.join(MEMORY_ROOT, relativePath);

        // Ensure destination directory exists
        const destDir = path.dirname(memoryFile);
        if (!fs.existsSync(destDir)) {
            fs.mkdirSync(destDir, { recursive: true });
        }

        if (syncFile(vaultFile, memoryFile, 'vault-to-memory')) {
            syncedCount++;
        }
    }

    logSync(`Vault → memory sync completed: ${syncedCount} files synchronized`);
    return syncedCount;
}

/**
 * Synchronize memory to vault
 */
function syncMemoryToVault() {
    logSync('Starting memory → vault synchronization');

    const memoryFiles = getMarkdownFiles(MEMORY_ROOT);
    let syncedCount = 0;

    for (const memoryFile of memoryFiles) {
        const relativePath = path.relative(MEMORY_ROOT, memoryFile);
        const vaultFile = path.join(VAULT_ROOT, relativePath);

        // Ensure destination directory exists
        const destDir = path.dirname(vaultFile);
        if (!fs.existsSync(destDir)) {
            fs.mkdirSync(destDir, { recursive: true });
        }

        if (syncFile(memoryFile, vaultFile, 'memory-to-vault')) {
            syncedCount++;
        }
    }

    logSync(`Memory → vault sync completed: ${syncedCount} files synchronized`);
    return syncedCount;
}

/**
 * Perform bidirectional synchronization
 */
function syncBidirectional() {
    logSync('Starting bidirectional vault-memory synchronization');
    const startTime = Date.now();

    try {
        // Sync vault to memory first
        const vaultToMemoryCount = syncVaultToMemory();

        // Then sync memory to vault
        const memoryToVaultCount = syncMemoryToVault();

        const endTime = Date.now();
        const duration = ((endTime - startTime) / 1000).toFixed(2);

        logSync(`Bidirectional sync completed in ${duration}s: ` +
                `${vaultToMemoryCount} vault→memory, ${memoryToVaultCount} memory→vault`);

        return {
            vaultToMemory: vaultToMemoryCount,
            memoryToVault: memoryToVaultCount,
            duration: parseFloat(duration)
        };
    } catch (error) {
        logSync(`Error during bidirectional sync: ${error.message}`);
        throw error;
    }
}

/**
 * Check if we're in a git repository and vault is clean
 * @returns {boolean} True if vault is in clean state
 */
function checkVaultGitStatus() {
    try {
        // Change to vault directory
        process.chdir(VAULT_ROOT);

        // Check if this is a git repo
        execSync('git rev-parse --is-inside-work-tree', { stdio: 'ignore' });

        // Check for uncommitted changes
        const status = execSync('git status --porcelain', { encoding: 'utf8' });
        const isClean = status.trim() === '';

        if (!isClean) {
            logSync('Warning: Vault has uncommitted changes');
            console.log('Unchanged files in vault:');
            console.log(status);
        }

        return isClean;
    } catch (error) {
        logSync(`Error checking vault git status: ${error.message}`);
        return false; // Assume not clean if we can't check
    } finally {
        // Return to original directory
        process.chdir(path.join(__dirname, '..'));
    }
}

/**
 * Main synchronization function
 * @param {string} direction - 'vault-to-memory', 'memory-to-vault', or 'bidirectional'
 */
function main(direction = 'bidirectional') {
    logSync(`Starting synchronization: ${direction}`);

    // Check vault git status before syncing
    const vaultClean = checkVaultGitStatus();
    if (!vaultClean && direction !== 'memory-to-vault') {
        logSync('Warning: Vault has uncommitted changes. Proceeding with caution.');
    }

    let result;

    switch (direction) {
        case 'vault-to-memory':
            result = { vaultToMemory: syncVaultToMemory(), memoryToVault: 0 };
            break;
        case 'memory-to-vault':
            result = { vaultToMemory: 0, memoryToVault: syncMemoryToVault() };
            break;
        case 'bidirectional':
        default:
            result = syncBidirectional();
            break;
    }

    logSync(`Synchronization finished: ${JSON.stringify(result)}`);
    return result;
}

// If script is run directly, execute synchronization
if (require.main === module) {
    const direction = process.argv[2] || 'bidirectional';
    try {
        main(direction);
        process.exit(0);
    } catch (error) {
        logSync(`Fatal error during synchronization: ${error.message}`);
        console.error(error);
        process.exit(1);
    }
}

module.exports = {
    syncVaultToMemory,
    syncMemoryToVault,
    syncBidirectional,
    main
};