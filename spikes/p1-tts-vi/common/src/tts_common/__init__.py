from .fake import FakeTTS, estimate_duration_s
from .normalize import normalize_vi, normalizer_for
from .pronunciations import (
    DEFAULT_PRONUNCIATIONS,
    PRONUNCIATIONS_BY_PROVIDER,
    load_pronunciations,
    pronunciations_for,
)
from .provider import Timing, TTSCost, TTSProvider, TTSResult
from .script import ScriptAudio, SentenceAudio, split_sentences, synthesize_script

__all__ = [
    "DEFAULT_PRONUNCIATIONS",
    "PRONUNCIATIONS_BY_PROVIDER",
    "FakeTTS",
    "ScriptAudio",
    "SentenceAudio",
    "TTSCost",
    "TTSProvider",
    "TTSResult",
    "Timing",
    "estimate_duration_s",
    "load_pronunciations",
    "normalize_vi",
    "normalizer_for",
    "pronunciations_for",
    "split_sentences",
    "synthesize_script",
]
