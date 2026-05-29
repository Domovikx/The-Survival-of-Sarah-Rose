#!/usr/bin/env node

/**
 * @module split_translations
 * @description Разделение/верификация Ren'Py переводов.
 * Разбивает единый файл переводов на файлы по аркам/сценам.
 *
 * Требования:
 * - Node.js >= 18 (использует fs.readFileSync, fs.writeFileSync, fs.readdirSync,
 *   fs.existsSync, fs.mkdirSync, path.join, path.relative)
 * - Никаких внешних зависимостей
 *
 * Использование:
 *   node split_translations.mjs split
 *   node split_translations.mjs verify
 *   node split_translations.mjs --source <path> --output <dir> split
 *
 * @see {@link https://nodejs.org/docs/latest-v18.x/api/fs.html|Node.js fs docs}
 */

import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * @type {Object<string, string[]>}
 */
const ARCHIVE_MAPPING = {
  Prologue: ['start', 'OpeningScene'],
  WarriorPath: ['Warrior', 'Hyral', 'GallowCreek'],
  MagePath: ['Mage', 'TheBlackMonolith', 'TheHollowWorld'],
  MarionPath: ['Marion', 'Varga', 'WarCouncil', 'CouncilMeeting', 'WarStrategy'],
  SailorPath: ['Sailor', 'Belmont', 'CallOut', 'EscapeLethram', 'NoMoney'],
  HassarPath: ['Hassar', 'Jaeid', 'Desert'],
  UnionKingdom: ['Union'],
  Relationships: ['Kate', 'Lily', 'Samayra', 'Nick', 'Carolyn', 'Cassius'],
  Bagrad: ['Bagrad', 'Bribe'],
  SakarPath: ['Sakar'],
  DemonArc: ['DemonArc', 'Razaphel'],
  Other: [],
};

/**
 * Разбивает строку по последнему разделителю (аналог Python str.rsplit).
 * @param {string} str
 * @param {string} separator
 * @param {number} [limit]
 * @returns {string[]}
 */
function rsplit(str, separator, limit) {
  const arr = str.split(separator);
  if (limit === undefined || arr.length <= limit) return arr;
  const last = arr.slice(-limit);
  const first = arr.slice(0, arr.length - limit).join(separator);
  return [first, ...last];
}

/**
 * Проверяет, является ли строка hex (6-8 символов).
 * @param {string} s
 * @returns {boolean}
 */
function isHex(s) {
  return s.length >= 6 && s.length <= 8 && /^[0-9a-f]+$/i.test(s);
}

/**
 * Извлекает имя сцены из ключа блока.
 * @param {string} key - например "HyralOrc2_c3fc8560" или "start_2b88e3eb"
 * @returns {string}
 */
export function getSceneName(key) {
  const parts = rsplit(key, '_', 1);
  if (parts.length === 1) return key;

  const last = parts[parts.length - 1];
  if (/^\d+$/.test(last)) {
    const parts2 = rsplit(parts[0], '_', 1);
    if (parts2.length > 1 && isHex(parts2[parts2.length - 1])) {
      return parts2[0];
    }
    return parts[0];
  }
  if (isHex(last)) {
    return parts[0];
  }
  return key;
}

/**
 * Определяет архив (арку) по имени сцены.
 * @param {string} sceneName
 * @returns {string}
 */
export function getArchive(sceneName) {
  for (const [archive, prefixes] of Object.entries(ARCHIVE_MAPPING)) {
    if (archive === 'Other') continue;
    for (const prefix of prefixes) {
      if (sceneName.startsWith(prefix)) return archive;
    }
  }
  return 'Other';
}

/**
 * Парсит .rpy файл на блоки translate ru <scene>_<hash>:
 * @param {string} filepath
 * @returns {Object<string, string[]>}
 */
export function parseRpy(filepath) {
  /** @type {Object<string, string[]>} */
  const blocks = {};
  let currentBlock = null;
  let currentKey = null;
  let skipNextEmpty = false;

  const content = readFileSync(filepath, 'utf-8');
  const lines = content.split('\n');

  for (const line of lines) {
    // Пропускаем # script.rpy:N строки
    if (/^# script\.rpy:\d+$/.test(line.trim())) continue;

    const match = /^translate ru ([A-Za-z0-9]+)_([a-f0-9]+)(?:_(\d+))?:$/.exec(line.trim());
    if (match) {
      if (currentKey && currentBlock) {
        blocks[currentKey] = currentBlock;
      }
      const sceneName = match[1];
      const hashPart = match[2];
      const suffix = match[3];
      currentKey = suffix !== undefined ? `${sceneName}_${hashPart}_${suffix}` : `${sceneName}_${hashPart}`;
      currentBlock = [line];
      skipNextEmpty = true;
    } else if (currentKey) {
      if (skipNextEmpty && line.trim() === '') {
        skipNextEmpty = false;
        continue;
      }
      currentBlock.push(line);
      skipNextEmpty = false;
    } else {
      if (line.trim() === '') {
        // Keep empty lines outside blocks
      }
    }
  }

  if (currentKey && currentBlock) {
    blocks[currentKey] = currentBlock;
  }

  return blocks;
}

/**
 * Разделяет исходный файл переводов на файлы по аркам.
 * @param {string} sourcePath - путь к исходному файлу
 * @param {string} outputDir - выходная директория
 * @param {string} [manifestDir] - директория для manifest.json
 * @returns {object} manifest
 */
export function splitTranslations(sourcePath, outputDir, manifestDir) {
  const source = sourcePath;
  const output = outputDir;
  const scriptDir = manifestDir || dirname(fileURLToPath(new URL('.', import.meta.url)));
  const manifestPath = join(scriptDir, 'manifest.json');

  // Clean output dir
  if (existsSync(output)) {
    cleanDir(output);
  }
  mkdirSync(output, { recursive: true });

  const blocks = parseRpy(source);

  /** @type {Object<string, string[]>} */
  const archiveFiles = {};
  let totalLines = 0;

  for (const [key, lines] of Object.entries(blocks)) {
    const sceneName = getSceneName(key);
    const archive = getArchive(sceneName);
    const archiveDir = join(output, archive);
    mkdirSync(archiveDir, { recursive: true });

    const filepath = join(archiveDir, `${sceneName}.rpy`);
    writeFileSync(filepath, lines.join('\n') + '\n', { flag: 'a', encoding: 'utf-8' });

    if (!archiveFiles[archive]) archiveFiles[archive] = [];
    if (!archiveFiles[archive].includes(sceneName)) {
      archiveFiles[archive].push(sceneName);
    }
    totalLines += lines.length;
  }

  const sourceContent = readFileSync(source, 'utf-8');
  const manifest = {
    archives: {},
    total_scenes: Object.keys(blocks).length,
    total_lines: totalLines,
    source_lines: sourceContent.split('\n').length,
  };

  for (const [archive, scenes] of Object.entries(archiveFiles)) {
    manifest.archives[archive] = {
      count: scenes.length,
      scenes: scenes.sort(),
    };
  }

  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf-8');

  return manifest;
}

/**
 * Рекурсивно очищает директорию.
 * @param {string} dir
 */
function cleanDir(dir) {
  if (!existsSync(dir)) return;
  const entries = readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      cleanDir(fullPath);
      try { rmSync(fullPath); } catch { /* ignore */ }
    } else {
      try { rmSync(fullPath); } catch { /* ignore */ }
    }
  }
}

/**
 * Проверяет целостность сплита.
 * @param {string} sourcePath
 * @param {string} outputDir
 * @param {string} [manifestDir]
 * @returns {object}
 */
export function verifyConsistency(sourcePath, outputDir, manifestDir) {
  const source = sourcePath;
  const output = outputDir;
  const scriptDir = manifestDir || dirname(fileURLToPath(new URL('.', import.meta.url)));
  const manifestPath = join(scriptDir, 'manifest.json');

  if (!existsSync(manifestPath)) {
    return { valid: false, error: 'manifest.json not found' };
  }

  const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));

  let totalOutputLines = 0;

  function countLines(dir) {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        countLines(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.rpy')) {
        const content = readFileSync(fullPath, 'utf-8');
        const lines = content.split('\n');
        const count = content.endsWith('\n') ? lines.length - 1 : lines.length;
        totalOutputLines += count;
      }
    }
  }
  countLines(output);

  return {
    valid: manifest.total_lines === totalOutputLines,
    source_lines: manifest.source_lines,
    output_lines: totalOutputLines,
    manifest_total_lines: manifest.total_lines,
    manifest_source_lines: manifest.source_lines,
  };
}

/**
 * CLI entry point.
 */
function main() {
  const args = process.argv.slice(2);

  const scriptDir = dirname(fileURLToPath(new URL('.', import.meta.url)));
  const gameDir = join(scriptDir, '..', '..', '..');

  let sourcePath = join(gameDir, 'game', 'tl', 'ru', 'script', '__.script.__rpy');
  let outputDir = join(gameDir, 'game', 'tl', 'ru', 'script', 'split');
  let manifestDir = scriptDir;
  let command = 'split';

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--source') sourcePath = args[++i];
    else if (args[i] === '--output') outputDir = args[++i];
    else if (args[i] === '--manifest') manifestDir = args[++i];
    else if (args[i] === 'split' || args[i] === 'verify') command = args[i];
  }

  if (command === 'verify') {
    const result = verifyConsistency(sourcePath, outputDir, manifestDir);
    console.log(`Valid: ${result.valid}`);
    console.log(`Source lines: ${result.source_lines}`);
    console.log(`Output lines: ${result.output_lines}`);
  } else {
    const manifest = splitTranslations(sourcePath, outputDir, manifestDir);
    console.log(`Split ${manifest.total_scenes} scenes into ${outputDir}`);
    for (const [archive, data] of Object.entries(manifest.archives)) {
      console.log(`  ${archive}: ${data.count} scenes`);
    }
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
