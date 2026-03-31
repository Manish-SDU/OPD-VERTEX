"""Download Faster-Whisper models for offline use."""

import os
from pathlib import Path
from faster_whisper import WhisperModel


def download_models():
    """Download Faster-Whisper models."""
    models_dir = Path(__file__).parent.parent / "models" / "whisper"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Set HuggingFace cache to our models directory
    os.environ["HF_HOME"] = str(models_dir)

    # Download models
    model_sizes = ["base"]  # Add "small", "medium" if needed

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
