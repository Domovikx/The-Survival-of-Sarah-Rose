"""voicekit — ядро TSSR voice pipeline.

Единственный источник правды по раскладке проекта (paths), загрузке
каталога/голосов/каста (catalog), контракту каста (contract), безопасным
файловым операциям (fs) и окружению TTS (tts_env).
"""

from . import paths, catalog, contract, fs, tts_env  # noqa: F401