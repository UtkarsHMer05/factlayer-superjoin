"""One command launches the API and worker; production assets are served by FastAPI."""
import os
import subprocess
import sys
import time

processes = []
try:
    processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.factlayer.api:app', '--host', os.getenv('HOST', '127.0.0.1'), '--port', os.getenv('PORT', '8017')]))
    if os.getenv('FACT_SAMPLE_MODE', '').lower() not in ('1', 'true'):
        processes.append(subprocess.Popen([sys.executable, '-m', 'backend.factlayer.worker']))
    while all(p.poll() is None for p in processes):
        time.sleep(1)
finally:
    for p in processes:
        p.terminate()
    for p in processes:
        p.wait(timeout=10)
