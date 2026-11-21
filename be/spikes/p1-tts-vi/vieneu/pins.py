"""Ghim revision (commit HF) cho model VieNeu. Đổi revision = phải review lại (README, mục trust_remote_code).

SDK `vieneu` không có tham số `revision`, nên ta tải đúng commit bằng `snapshot_download(revision=...)`
rồi đưa ĐƯỜNG DẪN CỤC BỘ cho SDK. Khi đó `trust_remote_code` chỉ chạy file .py nằm trong snapshot đã ghim.
"""

from __future__ import annotations

from huggingface_hub import snapshot_download

VIENEU_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
MOSS_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano"  # chứa mã remote (chỉ backend PyTorch)
MOSS_ONNX_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"  # chỉ ONNX graph, không có mã Python

REVISIONS = {
    VIENEU_REPO: "61b85e3d937fbbacb387714180e8182823512523",
    MOSS_REPO: "6aa02b01e445cc585582cf0ba480bc3ea6c8dd68",
    MOSS_ONNX_REPO: "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae",
}

# sha256 của 2 file Python mà trust_remote_code sẽ chạy (backend PyTorch); BE diff với bản tải về
REMOTE_CODE_SHA256 = {
    "configuration_moss_audio_tokenizer.py": (
        "b2d67dc4581e70f4b69b2d7eccefe32581d0c5192fe4d97fe1830e94a255b8aa"
    ),
    "modeling_moss_audio_tokenizer.py": ("b14af7c188944da5101adbd4aaa9c3617d66b83507f0efbd6eb416381a105930"),
}

# chỉ tải file cần dùng (không kéo cả repo)
_VIENEU_FILES = [
    "config.json",
    "speaker_encoder.onnx",
    "denoiser.onnx",
    "update/*",
    "onnx_update/*",
]
_MOSS_FILES = ["*.json", "*.py", "*.safetensors", "*.bin"]


def pinned(repo: str, allow_patterns: list[str] | None = None) -> str:
    """Đường dẫn snapshot cục bộ của đúng commit đã ghim (tải nếu chưa có)."""
    return snapshot_download(repo, revision=REVISIONS[repo], allow_patterns=allow_patterns)


def vieneu_kwargs(backend: str) -> dict[str, str]:
    """Tham số cho `Vieneu(mode="v3turbo", ...)` để mọi thứ được tải từ commit đã ghim."""
    backbone = pinned(VIENEU_REPO, _VIENEU_FILES)
    if backend == "onnx":
        return {"backbone_repo": backbone, "onnx_dir": f"{backbone}/onnx_update"}
    return {"backbone_repo": backbone, "moss_tokenizer": pinned(MOSS_REPO, _MOSS_FILES)}
