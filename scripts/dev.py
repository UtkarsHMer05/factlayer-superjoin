"""Launch the API, then its worker only after the API is ready."""
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


def ensure_port_available(host: str, port: str) -> None:
    """Catch a local port collision before spawning a worker."""
    try:
        with socket.socket(socket.AF_INET6 if ':' in host else socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((host, int(port)))
    except OSError as exc:
        raise RuntimeError(
            f'Cannot start FactLayer: port {port} is already in use. '
            f'Stop the existing server or run with PORT=<unused-port> make dev.'
        ) from exc


def wait_for_api(process: subprocess.Popen, host: str, port: str, timeout: float = 15) -> None:
    """Fail before starting the worker when Uvicorn cannot bind or start."""
    probe_host = '127.0.0.1' if host in {'0.0.0.0', '::'} else host
    url = f'http://{probe_host}:{port}/api/health'
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(
                f'API exited before becoming ready (exit code {exit_code}). '
                f'Port {port} may already be in use.'
            )
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.1)
    raise RuntimeError(f'API did not become ready at {url} within {timeout:g} seconds.')


def stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        if process.poll() is None:
            process.wait(timeout=10)


def main() -> None:
    host = os.getenv('HOST', '127.0.0.1')
    port = os.getenv('PORT', '8017')
    processes: list[subprocess.Popen] = []
    try:
        ensure_port_available(host, port)
        api = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'backend.factlayer.api:app',
            '--host', host, '--port', port,
        ])
        processes.append(api)
        wait_for_api(api, host, port)
        if os.getenv('FACT_SAMPLE_MODE', '').lower() not in {'1', 'true'}:
            processes.append(subprocess.Popen([sys.executable, '-m', 'backend.factlayer.worker']))
        while all(process.poll() is None for process in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop(processes)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print(f'FactLayer could not start: {exc}', file=sys.stderr)
        raise SystemExit(1) from exc
