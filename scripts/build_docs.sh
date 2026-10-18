#!/usr/bin/env bash
# Rebuild README screenshots + Architecture/Presentation PDFs with headless Chrome.
# Needs the server running:  python run.py --no-browser
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
URL="${URL:-http://127.0.0.1:8000}"
F=(--headless=new --enable-unsafe-swiftshader --use-angle=swiftshader --hide-scrollbars --virtual-time-budget=24000)
IMG=docs/images
mkdir -p "$IMG"
shot() {  # name WxH hash
  for i in 1 2 3; do
    "$CHROME" "${F[@]}" --window-size="$2" --screenshot="$IMG/$1.png" "$URL/#$3&fast=1" 2>/dev/null || true
    [ "$(stat -f%z "$IMG/$1.png" 2>/dev/null || stat -c%s "$IMG/$1.png")" -gt 600000 ] && break
  done
  echo "  $1"
}
echo "Screenshots"
shot dashboard       1600,1000 "pid=SNJ-001&t=16575"
shot forecast_full   1600,2000 "pid=SNJ-001&t=16575&tab=forecast"
shot whatif_full     1600,1560 "pid=SNJ-001&t=16575&tab=whatif&opt=1"
shot insights_full   1600,1900 "pid=SNJ-001&t=16575&tab=insights"
shot modelcard_full  1600,2300 "pid=SNJ-001&t=16575&tab=model"
shot physiology_full 1600,1500 "pid=SNJ-003&t=12000&tab=physiology"
shot records_full    1600,1600 "pid=SNJ-005&t=15000&tab=records"
shot organ           1600,1000 "pid=SNJ-001&t=16575&organ=pancreas"
crop() { cp "$IMG/$1.png" "$IMG/$2.png"; sips -c "$3" "$4" --cropOffset "$5" "$6" "$IMG/$2.png" >/dev/null; }
crop forecast_full forecast_crop 660 1600 1060 0
crop whatif_full   whatif_crop   500 1600 1060 0
crop whatif_full   ghost         790 870 240 330
crop insights_full insights_crop 840 1600 1060 0
echo "PDFs"
"$CHROME" --headless=new --hide-scrollbars --window-size=1587,1123 --virtual-time-budget=5000 --screenshot="$IMG/architecture.png" "file://$PWD/docs/src/architecture.html" 2>/dev/null
"$CHROME" --headless=new --no-pdf-header-footer --virtual-time-budget=5000 --print-to-pdf=docs/Architecture_Diagram.pdf "file://$PWD/docs/src/architecture.html" 2>/dev/null
"$CHROME" --headless=new --no-pdf-header-footer --virtual-time-budget=8000 --print-to-pdf=docs/Presentation.pdf "file://$PWD/docs/src/presentation.html" 2>/dev/null
ls -la docs/*.pdf
