"""One command to reproduce everything and open the dashboard.

    python run.py            # generate data + train (first run only), then serve
    python run.py --rebuild  # force regeneration and retraining
"""
import os
import sys
import webbrowser

os.environ.setdefault("OMP_NUM_THREADS", "2")
from sanjeevani.config import DATA_DIR, MODEL_DIR  # noqa: E402


def main():
    rebuild = "--rebuild" in sys.argv
    if rebuild or not (DATA_DIR / "manifest.json").exists():
        print("== Generating synthetic cohort (FHIR EHR + wearable streams) ==")
        from sanjeevani.synth import generate
        generate.main()
    need_train = rebuild or not any(MODEL_DIR.glob("models.pkl.gz.part*"))
    if not need_train:
        try:                                   # pickles from another scikit-learn version -> retrain
            import warnings
            from sanjeevani.pipeline import load_models
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                load_models()
        except Exception as e:
            print(f"Saved models not loadable here ({type(e).__name__}); retraining.")
            need_train = True
    if need_train:
        print("== Calibrating twins + training hybrid models (~5 min) ==")
        from sanjeevani import pipeline
        pipeline.main()
    port = next((a.split("=")[1] for a in sys.argv if a.startswith("--port=")), "8000")
    if "--no-browser" not in sys.argv:
        webbrowser.open(f"http://127.0.0.1:{port}")
    sys.argv = [sys.argv[0], "--port", port]
    from sanjeevani.api import server
    server.main()


if __name__ == "__main__":
    main()
