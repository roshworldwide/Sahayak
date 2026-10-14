#!/bin/bash
# Double-click in Finder to start the Sahayak node from this folder and open the app in the browser.
# Close the Terminal window (or press Ctrl+C) to stop it.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.pyenv/shims:$PATH"
need='import fastapi, uvicorn, numpy, sklearn, cv2, cryptography, qrcode, PIL'

# 1. a Python that already has Sahayak's packages (this folder's .venv, the usual places, then the PATH)
PY=""
for c in ./.venv/bin/python \
         "$HOME"/miniconda3/envs/*/bin/python "$HOME"/anaconda3/envs/*/bin/python "$HOME"/opt/anaconda3/envs/*/bin/python \
         "$HOME"/miniforge3/envs/*/bin/python "$HOME"/.pyenv/versions/*/bin/python "$HOME"/.venvs/*/bin/python \
         "$HOME"/miniconda3/bin/python "$HOME"/anaconda3/bin/python \
         /Library/Frameworks/Python.framework/Versions/*/bin/python3 \
         python3.11 python3.12 python3.13 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "$need" >/dev/null 2>&1; then PY="$c"; break; fi
done

# 2. none: make one in this folder (first time only, needs the internet for a few minutes)
if [ -z "$PY" ]; then
  echo "Setting up Sahayak's Python packages in .venv (first time only, needs the internet)..."
  python3 -m venv .venv && ./.venv/bin/python -m pip install --upgrade pip -q && ./.venv/bin/python -m pip install -r requirements.txt || {
    echo "Could not install the packages. Install them with: python3 -m pip install -r requirements.txt"; read -r -p "Press Return to close."; exit 1; }
  PY=./.venv/bin/python
fi
echo "Using $PY"

# 3. already running? just open it
if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Sahayak is already running on port 8000; opening it."
  open "http://localhost:8000/"
  exit 0
fi

IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo ""
echo "  Sahayak is starting."
echo "  On this Mac:            http://localhost:8000/"
[ -n "$IP" ] && echo "  Phones on the same Wi-Fi: http://$IP:8000/"
echo "  Close this window to stop it."
echo ""
( sleep 4; open "http://localhost:8000/" ) &
exec "$PY" -m sahayak
