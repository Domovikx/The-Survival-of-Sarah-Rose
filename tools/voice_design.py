#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Генерация кандидатов-голосов по текстовому описанию (Qwen3-TTS VoiceDesign).

ЧТО ДЕЛАЕТ:
  Для каждого выбранного персонажа генерирует N реплик-кандидатов
  (Qwen3-TTS-12Hz-1.7B-VoiceDesign, инструкция = instruct_en из YAML-каста)
  и кладёт их в voice_candidates/{Имя}/{NN}.mp3 (01.mp3, 02.mp3, ...).
  После прогона пишет статистику в voice_candidates/voice_candidates.yaml
  (дата, ok/skip/give_up/fail по каждому персонажу).

ИСТОЧНИК КАСТА (YAML):
  voice_candidates/{Имя}/{Имя}.yaml — описание голоса каждого персонажа:
    name, gender, age, who, instruct_en (англ. описание для модели), texts.
  Файл = контракт: добавил yaml -> персонаж появился в --list и генерации.
  Старый voice_design_cast.py УДАЛЁН — каст живёт только в yaml.

ПРАВИЛА (важно):
  1. Реф для CosyVoice3 должен быть >= 10с. Если клип вышел короче, тул
     автоматически повторяет генерацию: сначала с инструкцией «говори
     медленно», затем с удлинённым текстом (text + следующий текст).
  2. Тексты в касте содержат явный признак пола («я пошёл/пошла»,
     «я делал/делала») — это заставляет TTS уверенно выбирать пол голоса.
  3. Постобработка: убирается ведущая тишина, mp3 24 kHz mono 96k.
  4. Тул резюмабелен: существующие NN.mp3 не пересоздаются.
     Чтобы перегенерировать — удали файл (или используй --force).

ЗАПУСК (нужен python с пакетом qwen_tts — venv pinokio-приложения Qwen3-TTS,
в cosyvoice-venv пакета нет; модель VoiceDesign должна лежать в HF-кэше):
  C:\\pinokio\\api\\Qwen3-TTS-Pinokio.git\\app\\venv\\Scripts\\python.exe ^
      tools/voice_design.py --list
  ... tools/voice_design.py --char Carolyn --n 6
  ... tools/voice_design.py --n 3            # все голоса из каста, по 3 шт
  ... tools/voice_design.py --char Narrator --n 10 --force

CPU: ~1-2 мин на клип (1.7B, torch+cpu). 15 голосов x 6 = ~3-5 часов —
запускай на ночь или частями (тул дозапускается без повторов).
"""

import argparse
import glob
import os
import subprocess
import sys
import time
import traceback

try:
    import yaml
except ImportError:
    sys.exit("PyYAML не найден (нужен для чтения каста voice_candidates/*.yaml). "
             "Установи: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES_DIR = os.path.join(ROOT, 'voice_candidates')
LOG_PATH = os.path.join(ROOT, 'tools', 'voice_design.log')


def load_cast():
    """Собрать каст из voice_candidates/*/*.yaml. {Имя: cfg}."""
    cast = {}
    for path in sorted(glob.glob(os.path.join(CANDIDATES_DIR, '*', '*.yaml'))):
        name = os.path.basename(os.path.dirname(path))
        with open(path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict) or not cfg.get('texts'):
            print("WARN: пропускаю {} (нет texts)".format(path))
            continue
        cfg.setdefault('instruct_en', '')
        cast[name] = cfg
    return cast

# qwen_tts стоит в pinokio-приложении Qwen3-TTS (не в venv пакетом) —
# ищем каталог приложения: env QWEN_TTS_APP или путь по умолчанию
QWEN_APP_CANDIDATES = [
    os.environ.get("QWEN_TTS_APP"),
    r"C:\pinokio\api\Qwen3-TTS-Pinokio.git\app",
]


def ensure_qwen_tts():
    """Подложить каталог приложения Qwen3-TTS в sys.path, если пакет не найден."""
    try:
        import qwen_tts  # noqa: F401
        return
    except ImportError:
        pass
    for p in QWEN_APP_CANDIDATES:
        if p and os.path.isdir(os.path.join(p, "qwen_tts")):
            sys.path.insert(0, p)
            return
    sys.exit("qwen_tts не найден. Укажи каталог приложения через env "
             "QWEN_TTS_APP или установи пакет qwen-tts в текущий venv.")

# модель VoiceDesign — ищем в HF-кэше (последний снепшот репо)
MODEL_HF = r"C:\Users\Domo\.cache\huggingface\hub\models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign\snapshots"

TEMPO = "темп речи спокойный, неторопливый, паузы короткие"
TEMPS = [0.8, 0.95, 1.1, 0.85, 1.0, 0.9, 0.8, 0.95, 1.1, 0.85]

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)


STATS_PATH = os.path.join(CANDIDATES_DIR, "voice_candidates.yaml")


def load_stats():
    if not os.path.exists(STATS_PATH):
        return {}
    try:
        with open(STATS_PATH, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def write_stats(stats, n):
    """Обновить voice_candidates.yaml: дата прогона + результат по персонажам."""
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = load_stats()
    if not doc or "generation" not in doc:
        doc = {"generation": {}}
    doc.setdefault("updated", now)
    doc["updated"] = now
    for char, per in stats.items():
        per = dict(per)
        per["last_run"] = now
        doc["generation"][char] = per
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    log("stats -> {}".format(STATS_PATH))


def find_snapshot():
    if not os.path.isdir(MODEL_HF):
        raise RuntimeError("Нет VoiceDesign в HF-кэше: " + MODEL_HF)
    for d in sorted(os.listdir(MODEL_HF)):
        p = os.path.join(MODEL_HF, d)
        if os.path.exists(os.path.join(p, "model.safetensors")):
            return p
    raise RuntimeError("Снепшот VoiceDesign не найден: " + MODEL_HF)


def postprocess(wav_path, mp3_path):
    """Убрать ведущую тишину, mp3 24 kHz mono 96k."""
    subprocess.run([
        FFMPEG, "-y", "-i", wav_path,
        "-af", "silenceremove=start_periods=1:start_duration=0.15:start_threshold=-50dB",
        "-ac", "1", "-ar", "24000", "-b:a", "96k", mp3_path,
    ], capture_output=True)


def gen_one(model, dst, char, cfg, i, n):
    """Один кандидат с автодобором длины >= 10с.
    Возвращает: "ok" | "skip" | "give_up" | "fail"."""
    import soundfile as sf
    if os.path.exists(dst):
        log("skip {} (exists)".format(dst))
        return "skip"
    texts = cfg["texts"]
    text = texts[i % len(texts)]
    extra = texts[(i + 1) % len(texts)]

    # YAML-формат: instruct_en (английский). Legacy fallback base+vars.
    if cfg.get("instruct_en"):
        base_instruct = cfg["instruct_en"]
    else:
        base_instruct = (cfg.get("base", "") + "; " +
                         cfg["vars"][i % len(cfg["vars"])]).strip("; ")
    if not base_instruct:
        log("FAIL {} #{}: нет instruct_en в {}".format(char, i + 1, dst))
        return "fail"

    attempts = [
        (base_instruct + "; " + TEMPO,
         text, TEMPS[i % len(TEMPS)]),
        (base_instruct + "; " + TEMPO +
         "; speak slowly, deliberately, stretching words", text, 0.85),
        (base_instruct + "; " + TEMPO +
         "; speak slowly, deliberately, stretching words",
         text + " " + extra, 0.85),
    ]
    for att, (instruct, t, temp) in enumerate(attempts):
        log("== {} #{}/{} try{}".format(char, i + 1, n, att + 1))
        try:
            t1 = time.time()
            wavs, sr = model.generate_voice_design(
                text=t, instruct=instruct, language="Russian",
                do_sample=True, temperature=temp, top_p=0.9,
                max_new_tokens=4096)
            gen_s = time.time() - t1
            dur = len(wavs[0]) / sr
            wav_tmp = dst.replace(".mp3", ".wav")
            sf.write(wav_tmp, wavs[0], sr)
            postprocess(wav_tmp, dst)
            os.remove(wav_tmp)
            d2 = float(subprocess.check_output(
                [FFPROBE, "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", dst]).decode().strip())
            if d2 >= 10.0:
                log("OK try{} gen {:.1f}s raw {:.1f}s -> {:.1f}s".format(
                    att + 1, gen_s, dur, d2))
                return "ok"
            log("SHORT try{} raw {:.1f}s -> {:.1f}s".format(att + 1, dur, d2))
        except Exception:
            log("FAIL {} #{} try{}:\n{}".format(char, i + 1, att + 1,
                                                traceback.format_exc()))
            return "fail"
    log("GIVE UP {} #{}/{}".format(char, i + 1, n))
    return "give_up"


def main():
    ap = argparse.ArgumentParser(description="Генерация кандидатов-голосов "
                                             "(Qwen3-TTS VoiceDesign)")
    ap.add_argument('--char', action='append', default=None,
                    help='только этот персонаж (можно несколько раз)')
    ap.add_argument('--n', type=int, default=3,
                    help='сколько кандидатов на голос (default 3)')
    ap.add_argument('--list', action='store_true', help='показать каст и выйти')
    ap.add_argument('--force', action='store_true',
                    help='перегенерировать существующие файлы кандидатов')
    args = ap.parse_args()

    cast = load_cast()
    if not cast:
        print("Каст пуст: нет voice_candidates/*/*.yaml")
        return 1

    if args.list:
        for name, cfg in sorted(cast.items()):
            print("{:24} {} текстов | {}".format(
                name, len(cfg["texts"]), (cfg.get("instruct_en") or
                                          cfg.get("base") or "")[:60]))
        return 0

    if args.char:
        missing = [c for c in args.char if c not in cast]
        if missing:
            print("Нет в касте: {}".format(", ".join(missing)))
            print("Есть: " + ", ".join(sorted(cast)))
            return 1
        todo = {c: cast[c] for c in args.char}
    else:
        todo = cast

    snap = find_snapshot()
    ensure_qwen_tts()
    import torch  # noqa: F401
    from qwen_tts import Qwen3TTSModel
    log("loading model from {}".format(snap))
    model = Qwen3TTSModel.from_pretrained(snap, device_map="cpu",
                                          dtype=torch.float32)
    log("model loaded")

    total = 0
    stats = {}
    for char, cfg in todo.items():
        dst_dir = os.path.join(CANDIDATES_DIR, char)
        os.makedirs(dst_dir, exist_ok=True)
        per_char = {"n": args.n, "ok": 0, "skip": 0, "give_up": 0, "fail": 0}
        for i in range(args.n):
            dst = os.path.join(dst_dir, "{:02d}.mp3".format(i + 1))
            if args.force and os.path.exists(dst):
                os.remove(dst)
            res = gen_one(model, dst, char, cfg, i, args.n)
            per_char[res] += 1
            if res == "ok":
                total += 1
        stats[char] = per_char
    write_stats(stats, args.n)
    log("DONE total: {}".format(total))


if __name__ == "__main__":
    main()
