#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сводная статистика каста голосов -> voice_candidates/voice_candidates.yaml.

ЧТО ДЕЛАЕТ:
  Сканирует voice_candidates/{Имя}/{Имя}.yaml + refs/ и пересобирает
  voice_candidates.yaml:
    - summary: всего/с голосом/без голоса/с кандидатами
    - cast: по каждому персонажу gender, age, status, candidates, ref
    - generation: история прогонов voice_design.py (сохраняется как есть)

ЗАПУСК:
  python tools/voice_design_stats.py

После генерации voice_design.py сам дописывает секцию generation.
Этот скрипт обновляет только summary/cast, generation не трогает.
"""

import datetime
import glob
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML не найден. Установи: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(ROOT, "voice_candidates")
REFS = os.path.join(ROOT, "refs")
STATS = os.path.join(CAND, "voice_candidates.yaml")


def main():
    if not os.path.isdir(REFS):
        print("WARN: нет refs/ — считаю голоса по refs/{Name}.wav")

    cast = {}
    for f in sorted(glob.glob(os.path.join(CAND, "*", "*.yaml"))):
        name = os.path.basename(os.path.dirname(f))
        with open(f, encoding="utf-8") as fh:
            d = yaml.safe_load(fh) or {}
        cand_dir = os.path.join(CAND, name)
        cands = sorted(x for x in os.listdir(cand_dir)
                       if x.endswith(".mp3") and not x.startswith("."))
        ref = os.path.join(REFS, name + ".wav")
        if os.path.exists(ref):
            status = "voice_ready"
        elif cands:
            status = "candidates"
        else:
            status = "need_generation"
        cast[name] = {
            "gender": d.get("gender"),
            "age": d.get("age"),
            "status": status,
            "candidates": len(cands),
            "ref": os.path.basename(ref) if os.path.exists(ref) else None,
        }

    doc = {}
    if os.path.exists(STATS):
        with open(STATS, encoding="utf-8") as fh:
            old = yaml.safe_load(fh) or {}
        if isinstance(old, dict):
            doc = old

    n_all = len(cast)
    n_voice = sum(1 for v in cast.values() if v["status"] == "voice_ready")
    n_cand = sum(1 for v in cast.values() if v["status"] == "candidates")
    n_none = sum(1 for v in cast.values() if v["status"] == "need_generation")

    doc["updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    doc["summary"] = {
        "total": n_all,
        "voice_ready": n_voice,
        "candidates": n_cand,
        "need_generation": n_none,
    }
    doc["cast"] = cast
    doc.setdefault("generation", {})

    with open(STATS, "w", encoding="utf-8") as fh:
        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False)

    print("total={} voice_ready={} candidates={} need={}".format(
        n_all, n_voice, n_cand, n_none))
    print("-> {}".format(STATS))


if __name__ == "__main__":
    main()