#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Генерация кандидатов-голосов по текстовому описанию (Qwen3-TTS VoiceDesign).

ЧТО ДЕЛАЕТ:
  Для каждого выбранного персонажа из tools/voice_design_cast.py генерирует
  N реплик-кандидатов (Qwen3-TTS-12Hz-1.7B-VoiceDesign, инструкция = описание
  голоса из каста) и кладёт их в voice_candidates/{Имя}/qwen_NN.mp3.

ПРАВИЛА (важно):
  1. Реф для CosyVoice3 должен быть >= 10с. Если клип вышел короче, тул
     автоматически повторяет генерацию: сначала с инструкцией «говори
     медленно», затем с удлинённым текстом (text + следующий текст).
  2. Тексты в касте содержат явный признак пола («я пошёл/пошла»,
     «я делал/делала») — это заставляет TTS уверенно выбирать пол голоса.
  3. Постобработка: убирается ведущая тишина, mp3 24 kHz mono 96k.
  4. Тул резюмабелен: существующие qwen_NN.mp3 не пересоздаются.
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
import os
import subprocess
import sys
import time
import traceback

# импорт каста из этого же каталога tools/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voice_design_cast import CHARS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES_DIR = os.path.join(ROOT, 'voice_candidates')
LOG_PATH = os.path.join(ROOT, 'tools', 'voice_design.log')

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
    """Один кандидат с автодобором длины >= 10с. True если готов."""
    import soundfile as sf
    if os.path.exists(dst):
        log("skip {} (exists)".format(dst))
        return True
    texts = cfg["texts"]
    text = texts[i % len(texts)]
    extra = texts[(i + 1) % len(texts)]
    attempts = [
        (cfg["base"] + "; " + cfg["vars"][i % len(cfg["vars"])] + "; " + TEMPO,
         text, TEMPS[i % len(TEMPS)]),
        (cfg["base"] + "; " + cfg["vars"][i % len(cfg["vars"])] + "; " + TEMPO +
         "; говори медленно, размеренно, растягивая слова", text, 0.85),
        (cfg["base"] + "; " + cfg["vars"][i % len(cfg["vars"])] + "; " + TEMPO +
         "; говори медленно, размеренно, растягивая слова",
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
                return True
            log("SHORT try{} raw {:.1f}s -> {:.1f}s".format(att + 1, dur, d2))
        except Exception:
            log("FAIL {} #{} try{}:\n{}".format(char, i + 1, att + 1,
                                                traceback.format_exc()))
            return False
    log("GIVE UP {} #{}/{}".format(char, i + 1, n))
    return False


def main():
    ap = argparse.ArgumentParser(description="Генерация кандидатов-голосов "
                                             "(Qwen3-TTS VoiceDesign)")
    ap.add_argument('--char', action='append', default=None,
                    help='только этот персонаж (можно несколько раз)')
    ap.add_argument('--n', type=int, default=3,
                    help='сколько кандидатов на голос (default 3)')
    ap.add_argument('--list', action='store_true', help='показать каст и выйти')
    ap.add_argument('--force', action='store_true',
                    help='перегенерировать существующие qwen-файлы')
    args = ap.parse_args()

    if args.list:
        for name, cfg in CHARS.items():
            print("{:24} {} текстов | {}".format(
                name, len(cfg["texts"]), cfg["base"][:60]))
        return 0

    if args.char:
        missing = [c for c in args.char if c not in CHARS]
        if missing:
            print("Нет в касте: {}".format(", ".join(missing)))
            print("Есть: " + ", ".join(sorted(CHARS)))
            return 1
        todo = {c: CHARS[c] for c in args.char}
    else:
        todo = CHARS

    snap = find_snapshot()
    ensure_qwen_tts()
    import torch  # noqa: F401
    from qwen_tts import Qwen3TTSModel
    log("loading model from {}".format(snap))
    model = Qwen3TTSModel.from_pretrained(snap, device_map="cpu",
                                          dtype=torch.float32)
    log("model loaded")

    total = 0
    for char, cfg in todo.items():
        dst_dir = os.path.join(CANDIDATES_DIR, char)
        os.makedirs(dst_dir, exist_ok=True)
        for i in range(args.n):
            dst = os.path.join(dst_dir, "qwen_{:02d}.mp3".format(i + 1))
            if args.force and os.path.exists(dst):
                os.remove(dst)
            if gen_one(model, dst, char, cfg, i, args.n):
                total += 1
    log("DONE total: {}".format(total))


if __name__ == "__main__":
    main()
