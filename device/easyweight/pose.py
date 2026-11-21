"""The MediaPipe pose model: downloading it and creating the landmarker."""
import os
import ssl
import sys
import urllib.request
from pathlib import Path

os.environ.setdefault("GLOG_minloglevel", "2")  # hide MediaPipe's startup log noise

from mediapipe.tasks import python as mp_tasks  # noqa: E402
from mediapipe.tasks.python import vision  # noqa: E402

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_{v}/float16/latest/pose_landmarker_{v}.task")
MODEL_SIZES_MB = {"lite": 6, "full": 9, "heavy": 31}
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def load_model(variant, models_dir=MODELS_DIR):
    """Return the model file's bytes, downloading it the first time"""
    models_dir = Path(models_dir)
    path = models_dir / f"pose_landmarker_{variant}.task"
    if not path.exists():
        models_dir.mkdir(parents=True, exist_ok=True)
        url = MODEL_URL.format(v=variant)
        print(f"Downloading the {variant} pose model "
              f"(about {MODEL_SIZES_MB[variant]} MB), one time only...")
        tmp = path.with_name(path.name + ".part")
        try:
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
            with urllib.request.urlopen(url, context=ctx, timeout=60) as resp, \
                    open(tmp, "wb") as f:
                while chunk := resp.read(1 << 16):
                    f.write(chunk)
            tmp.replace(path)
        except Exception as e:
            tmp.unlink(missing_ok=True)
            sys.exit(f"\nCouldn't download the model: {e}\n"
                     f"Download it in your browser from:\n  {url}\n"
                     f"and save it in {models_dir}, named {path.name}")
        print("Done.")
    # Reading the file ourselves (instead of giving MediaPipe the path) avoids
    # file path problems with non-English folder names on Windows
    return path.read_bytes()


def create_landmarker(model_bytes):
    options = vision.PoseLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_buffer=model_bytes),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,  # change these to be more/less strict
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.PoseLandmarker.create_from_options(options)
