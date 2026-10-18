"""Global configuration for the Sanjeevani digital twin."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PATIENT_DIR = DATA_DIR / "patients"
TRUTH_DIR = DATA_DIR / "_ground_truth"
MODEL_DIR = ROOT / "models"
DASHBOARD_DIR = ROOT / "dashboard"

IST = timezone(timedelta(hours=5, minutes=30))
START = datetime(2026, 10, 5, 0, 0, tzinfo=IST)   # Mon 5 Oct 2026
N_DAYS = 14
DAY = 1440
T_MIN = N_DAYS * DAY                              # minutes in the observation window
CGM_STEP = 5                                      # CGM / wearable sampling (min)

CALIB_DAYS = 3                                    # onboarding days used to calibrate a twin
ANCHOR_STEP = 15                                  # prediction cadence (min)
HORIZONS = (30, 60, 120)                          # forecast horizons (min)
QUANTILES = (0.1, 0.5, 0.9)

SPIKE_MGDL = 180                                  # ADA target-range upper bound
HYPO_MGDL = 70
SEVERE_MGDL = 250

# Sharad Navratri 2026: 11 Oct - 19 Oct (day indices inside the window)
NAVRATRI_DAYS = set(range(6, 14))
FESTIVALS = {6: "Navratri begins", 13: "Navratri - Ashtami/Navami"}

N_PATIENTS = 40
TEST_FRACTION = 0.25
SEED = 2026
