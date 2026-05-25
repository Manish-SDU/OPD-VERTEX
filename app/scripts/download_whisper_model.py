"""Download Faster-Whisper models for offline use."""

import os
from pathlib import Path
from faster_whisper import WhisperModel


def download_models():
    """Download Faster-Whisper models."""
    if not os.environ.get("HF_HOME"):
        models_dir = Path(__file__).parent.parent / "models" / "whisper"
        models_dir.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(models_dir)
    else:
        models_dir = Path(os.environ["HF_HOME"])
        models_dir.mkdir(parents=True, exist_ok=True)

    # Download models — large-v3 is the default production model
    model_size = os.environ.get("WHISPER_MODEL_NAME", "large-v3")
    model_sizes = [model_size]

    for size in model_sizes:
        print(f"Downloading Faster-Whisper {size} model...")
        try:
            # Don't pass cache_dir - use HF_HOME env var instead
            WhisperModel(size)
            print(f"✅ {size} model downloaded successfully to {models_dir}")
        except Exception as e:
            print(f"❌ Failed to download {size}: {e}")
            raise


if __name__ == "__main__":
    download_models()
