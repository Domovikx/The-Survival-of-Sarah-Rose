import { writeFileSync, mkdirSync, existsSync, readdirSync, rmSync } from 'fs';
import { join, dirname } from 'path';

const REPO = 'Domovikx/The-Survival-of-Sarah-Rose';
const BRANCH = 'master';
const TL_PATH = 'game/tl/ru';
const API = `https://api.github.com/repos/${REPO}/contents`;

async function* walkDir(path) {
    const url = `${API}/${path}?ref=${BRANCH}`;
    const res = await fetch(url, { headers: { 'User-Agent': 'translation-installer' } });
    if (!res.ok) throw new Error(`GitHub API error: ${res.status} ${res.statusText}`);
    const items = await res.json();
    for (const item of items) {
        if (item.type === 'dir') {
            yield* walkDir(item.path);
        } else if (item.type === 'file' && item.name.endsWith('.rpy')) {
            yield item;
        }
    }
}

function clearRenpyCache(gameDir) {
    const tlDir = join(gameDir, 'game', 'tl', 'ru');
    if (!existsSync(tlDir)) return 0;
    let count = 0;
    for (const file of readdirSync(tlDir, { recursive: true })) {
        if (file.endsWith('.rpyc')) {
            rmSync(join(tlDir, file));
            count++;
        }
    }
    return count;
}

async function main() {
    const gameDir = process.argv[2] || process.cwd();
    console.log(`\n=== The Survival of Sarah Rose — Russian Translation Installer ===\n`);
    console.log(`Game path: ${gameDir}\n`);

    const exePath = join(gameDir, 'TheSurvivalofSarahRose.exe');
    if (!existsSync(exePath)) {
        console.error(`ERROR: Cannot find TheSurvivalofSarahRose.exe in "${gameDir}"`);
        console.error(`Navigate to your game folder and run:`);
        console.error(`  node install.mjs "C:\\Path\\To\\Game"`);
        process.exit(1);
    }

    let count = 0;
    for await (const file of walkDir(TL_PATH)) {
        const localPath = join(gameDir, file.path);
        const localDir = dirname(localPath);
        mkdirSync(localDir, { recursive: true });

        const res = await fetch(file.download_url);
        if (!res.ok) throw new Error(`Download failed: ${file.name}`);
        const content = await res.text();
        writeFileSync(localPath, content, 'utf-8');
        count++;
    }

    console.log(`\nDownloaded: ${count} files`);

    const cacheCount = clearRenpyCache(gameDir);
    if (cacheCount > 0) {
        console.log(`Cache cleared: ${cacheCount} .rpyc files removed`);
    }

    console.log(`\nDone! Launch the game and select Russian in Settings.\n`);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
