"""Split existing models for Vercel's per-file upload limit; never download/train."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / ".runtime-upload"
MODELS = {
    "embedding": "ml/artifacts/embedding_model/model.safetensors",
    "whisper": "stt/models/ggml-base.bin",
}


def prepare():
    OUTPUT.mkdir(exist_ok=True)
    checksums = []
    for name, relative in MODELS.items():
        digest = hashlib.sha256()
        count = 0
        with (ROOT / relative).open("rb") as source:
            while block := source.read(64 * 1024 * 1024):
                digest.update(block)
                (OUTPUT / f"{name}.part{count:03d}").write_bytes(block)
                count += 1
        for stale in OUTPUT.glob(f"{name}.part*"):
            if int(stale.suffix.removeprefix(".part")) >= count:
                stale.unlink()
        checksums.append(f"{digest.hexdigest()}  {relative}")
        print(f"{relative}: {count} chunks, SHA-256 {digest.hexdigest()}")
    (OUTPUT / "SHA256SUMS").write_text("\n".join(checksums) + "\n")


if __name__ == "__main__":
    prepare()
