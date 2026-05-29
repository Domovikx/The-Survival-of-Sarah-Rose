/**
 * Tests for split_translations.mjs
 * ================================
 *
 * Требования:
 * - Node.js >= 18 (использует node:test, node:assert/strict)
 * - Никаких внешних зависимостей
 *
 * Запуск:
 *   node --test split_translations.test.mjs
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, readFileSync, mkdirSync, rmSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import {
  splitTranslations, verifyConsistency, getArchive, parseRpy, getSceneName,
} from './split_translations.mjs';

// ─── Helpers ──────────────────────────────────────────────────

function makeTempDir(prefix = 'split-test-') {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  return {
    path: dir,
    cleanup: () => rmSync(dir, { recursive: true, force: true }),
  };
}

const sampleRpy = [
  '# TODO: Translation updated at 2026-05-08 00:19',
  '',
  '# script.rpy:34',
  'translate ru start_2b88e3eb:',
  '',
  '    # "«Survival of Sarah Rose» is an epic fantasy game. TSSR development is still ongoing."',
  '    "«Выживание Сары Роуз» — эпическая фэнтези-игра. Разработка TSSR всё ещё продолжается."',
  '',
  '# script.rpy:309',
  'translate ru OpeningScene_7a765a1f:',
  '',
  '    # "Castle Reinmeer"',
  '    "Замок Рейнмир"',
  '',
  '# script.rpy:333',
  'translate ru OpeningSceneFirstMorning_9e6c896e:',
  '',
  '    # "Sarah wakes to the first beams of light breaking through her curtains."',
  '    ""',
  '',
  '# script.rpy:702',
  'translate ru OpeningSceneFirstMorning_2c781ead_1:',
  '',
  '    # "She watches herself in the mirror as she tries out a series of different dresses."',
  '    ""',
  '',
].join('\n');

// ─── Tests: getArchive ────────────────────────────────────────

describe('getArchive', () => {
  it('Prologue scenes', () => {
    assert.equal(getArchive('start'), 'Prologue');
    assert.equal(getArchive('OpeningScene'), 'Prologue');
    assert.equal(getArchive('OpeningSceneSequence2'), 'Prologue');
  });

  it('WarriorPath scenes', () => {
    assert.equal(getArchive('WarriorQueen1'), 'WarriorPath');
    assert.equal(getArchive('HyralOrc'), 'WarriorPath');
    assert.equal(getArchive('GallowCreek1'), 'WarriorPath');
  });

  it('MagePath scenes', () => {
    assert.equal(getArchive('MagePath'), 'MagePath');
    assert.equal(getArchive('TheBlackMonolithMage1'), 'MagePath');
    assert.equal(getArchive('TheHollowWorldWarrior1'), 'MagePath');
  });

  it('MarionPath scenes', () => {
    assert.equal(getArchive('MarionPath'), 'MarionPath');
    assert.equal(getArchive('WarCouncil'), 'MarionPath');
    assert.equal(getArchive('VargaPath1'), 'MarionPath');
  });

  it('SailorPath scenes', () => {
    assert.equal(getArchive('SailorPath1'), 'SailorPath');
    assert.equal(getArchive('BelmontTalkback'), 'SailorPath');
  });

  it('Other scenes', () => {
    assert.equal(getArchive('SomeUnknownScene'), 'Other');
    assert.equal(getArchive('RandomName'), 'Other');
  });
});

// ─── Tests: parseRpy ──────────────────────────────────────────

describe('parseRpy', () => {
  it('parses blocks from sample', () => {
    const tmp = makeTempDir();
    try {
      const filePath = join(tmp.path, 'sample.rpy');
      writeFileSync(filePath, sampleRpy, 'utf-8');

      const blocks = parseRpy(filePath);
      assert.ok('start_2b88e3eb' in blocks);
      assert.ok('OpeningScene_7a765a1f' in blocks);
      assert.ok('OpeningSceneFirstMorning_2c781ead_1' in blocks);
      assert.equal(Object.keys(blocks).length, 4);
    } finally {
      tmp.cleanup();
    }
  });

  it('parses blocks with numbered scenes', () => {
    const tmp = makeTempDir();
    try {
      const filePath = join(tmp.path, 'numbered.rpy');
      writeFileSync(filePath, [
        'translate ru HyralOrc_c3fc8560:',
        '',
        '    # "Original text"',
        '    "Translated"',
        '',
        'translate ru HyralOrc2_d4cd0950:',
        '',
        '    # "Another text"',
        '    "Another translated"',
        '',
      ].join('\n'), 'utf-8');

      const blocks = parseRpy(filePath);
      assert.ok('HyralOrc_c3fc8560' in blocks);
      assert.ok('HyralOrc2_d4cd0950' in blocks);
      assert.equal(Object.keys(blocks).length, 2);
    } finally {
      tmp.cleanup();
    }
  });
});

// ─── Tests: getSceneName ──────────────────────────────────────

describe('getSceneName', () => {
  it('extracts scene name', () => {
    assert.equal(getSceneName('start'), 'start');
    assert.equal(getSceneName('OpeningSceneFirstMorning'), 'OpeningSceneFirstMorning');
    assert.equal(getSceneName('OpeningSceneFirstMorning_2'), 'OpeningSceneFirstMorning');
  });

  it('handles scene name with trailing number', () => {
    assert.equal(getSceneName('HyralOrc2_c3fc8560'), 'HyralOrc2');
    assert.equal(getSceneName('SailorPath10_b1646d8b'), 'SailorPath10');
    assert.equal(getSceneName('TheOldRoad5_1336f621'), 'TheOldRoad5');
    assert.equal(getSceneName('UnionKingdom2_7f7d77be'), 'UnionKingdom2');
  });
});

// ─── Tests: splitTranslations ─────────────────────────────────

describe('splitTranslations', () => {
  it('creates directories and splits correctly', () => {
    const tmp = makeTempDir();
    try {
      const sourcePath = join(tmp.path, 'source.rpy');
      writeFileSync(sourcePath, sampleRpy, 'utf-8');

      const outputDir = join(tmp.path, 'output');
      const manifest = splitTranslations(sourcePath, outputDir, tmp.path);

      assert.ok(existsSync(join(outputDir, 'Prologue')));
      assert.equal(manifest.total_scenes, 4);

      assert.ok(existsSync(join(outputDir, 'Prologue', 'start.rpy')));
      assert.ok(existsSync(join(outputDir, 'Prologue', 'OpeningScene.rpy')));
      assert.ok(existsSync(join(outputDir, 'Prologue', 'OpeningSceneFirstMorning.rpy')));
    } finally {
      tmp.cleanup();
    }
  });

  it('verify consistency', () => {
    const tmp = makeTempDir();
    try {
      const sourcePath = join(tmp.path, 'source.rpy');
      writeFileSync(sourcePath, sampleRpy, 'utf-8');

      const outputDir = join(tmp.path, 'output');
      splitTranslations(sourcePath, outputDir, tmp.path);

      const result = verifyConsistency(sourcePath, outputDir, tmp.path);
      assert.equal(result.valid, true);
    } finally {
      tmp.cleanup();
    }
  });
});

// ─── Tests: Duplicate Scenes ──────────────────────────────────

describe('duplicate scenes', () => {
  const sampleWithDuplicates = [
    '# script.rpy:100',
    'translate ru Scene_abc123:',
    '',
    '    # "Original text 1"',
    '    "Translated 1"',
    '',
    '# script.rpy:200',
    'translate ru Scene_def456_1:',
    '',
    '    # "Original text 2"',
    '    "Translated 2"',
    '',
    '# script.rpy:300',
    'translate ru Scene_def456_2:',
    '',
    '    # "Original text 3"',
    '    "Translated 3"',
    '',
    '# script.rpy:400',
    'translate ru Scene_ghi789_1:',
    '',
    '    # "Original text 4"',
    '    "Translated 4"',
    '',
  ].join('\n');

  it('duplicate scenes merged into one file', () => {
    const tmp = makeTempDir();
    try {
      const sourcePath = join(tmp.path, 'source.rpy');
      writeFileSync(sourcePath, sampleWithDuplicates, 'utf-8');

      const outputDir = join(tmp.path, 'output');
      const manifest = splitTranslations(sourcePath, outputDir, tmp.path);

      const sceneFile = join(outputDir, 'Other', 'Scene.rpy');
      assert.ok(existsSync(sceneFile));

      const content = readFileSync(sceneFile, 'utf-8');
      assert.ok(content.includes('Scene_def456_1'));
      assert.ok(content.includes('Scene_def456_2'));
      assert.ok(content.includes('Original text 2'));
      assert.ok(content.includes('Original text 3'));

      const allScenes = [];
      for (const archiveData of Object.values(manifest.archives)) {
        allScenes.push(...archiveData.scenes);
      }
      assert.ok(allScenes.includes('Scene'));
    } finally {
      tmp.cleanup();
    }
  });

  it('duplicate count matches', () => {
    const tmp = makeTempDir();
    try {
      const sourcePath = join(tmp.path, 'source.rpy');
      writeFileSync(sourcePath, sampleWithDuplicates, 'utf-8');

      const outputDir = join(tmp.path, 'output');
      splitTranslations(sourcePath, outputDir, tmp.path);

      const sourceContent = readFileSync(sourcePath, 'utf-8');
      const sourceBlocks = sourceContent.split('\n').filter(l => l.startsWith('translate ru ')).length;

      let chunkBlocks = 0;
      function countBlocks(dir) {
        const entries = readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          const fp = join(dir, entry.name);
          if (entry.isDirectory()) countBlocks(fp);
          else if (entry.isFile() && entry.name.endsWith('.rpy')) {
            const c = readFileSync(fp, 'utf-8');
            chunkBlocks += c.split('\n').filter(l => l.startsWith('translate ru ')).length;
          }
        }
      }
      countBlocks(outputDir);

      assert.equal(sourceBlocks, chunkBlocks, `Blocks mismatch: source=${sourceBlocks}, chunks=${chunkBlocks}`);
    } finally {
      tmp.cleanup();
    }
  });
});

// ─── End-to-End ───────────────────────────────────────────────

describe('end-to-end', () => {
  it('full workflow', () => {
    const tmp = makeTempDir();
    try {
      const sourcePath = join(tmp.path, 'source.rpy');
      writeFileSync(sourcePath, sampleRpy, 'utf-8');

      const outputDir = join(tmp.path, 'output');
      const manifest = splitTranslations(sourcePath, outputDir, tmp.path);

      const result = verifyConsistency(sourcePath, outputDir, tmp.path);
      assert.equal(result.valid, true);

      for (const [archive, data] of Object.entries(manifest.archives)) {
        for (const scene of data.scenes) {
          const scenePath = join(outputDir, archive, `${scene}.rpy`);
          assert.ok(existsSync(scenePath), `Missing: ${scenePath}`);
        }
      }
    } finally {
      tmp.cleanup();
    }
  });
});
