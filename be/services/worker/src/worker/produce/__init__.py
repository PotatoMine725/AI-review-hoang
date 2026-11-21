"""Đường ghép kịch bản M2 → TTS → render plan #88 → HyperFrames → MP4 (P1-08).

Phần chạy bằng code worker: kiểm kịch bản, ánh xạ M2 → plan, cache TTS, timeline, kiểm MP4, report.
Phần gọi spike qua subprocess (venv riêng, chưa port): VieNeu #73 (`drivers/tts_synth.py`) và
HyperFrames + FFmpeg #88 (`drivers/hf_render.py`).
"""
