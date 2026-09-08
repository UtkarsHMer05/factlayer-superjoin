import pytest

from scripts import dev


class ExitedProcess:
    def poll(self):
        return 1


def test_dev_fails_before_starting_worker_when_api_cannot_bind(monkeypatch):
    calls = []

    def fake_popen(command):
        calls.append(command)
        return ExitedProcess()

    monkeypatch.delenv('FACT_SAMPLE_MODE', raising=False)
    monkeypatch.setattr(dev, 'ensure_port_available', lambda *args: None)
    monkeypatch.setattr(dev.subprocess, 'Popen', fake_popen)

    with pytest.raises(RuntimeError, match='Port 8017 may already be in use'):
        dev.main()

    assert len(calls) == 1
