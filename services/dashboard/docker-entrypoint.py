#!/usr/bin/env python3
# The runtime stage of the Dockerfile uses a hardened image with no shell,
# so this replaces the previous `python init_db.py && exec gunicorn ...`
# shell-form CMD. os.execvp replaces this process the same way `exec` did,
# so gunicorn still receives signals (e.g. SIGTERM on `docker stop`) directly.
import os
import subprocess
import sys

subprocess.run([sys.executable, "init_db.py"], check=True)
os.execvp("gunicorn", ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "run:app"])
