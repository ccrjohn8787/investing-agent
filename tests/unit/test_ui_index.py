from __future__ import annotations

from pathlib import Path


def test_make_index(tmp_path, monkeypatch):
    out = tmp_path / "out"
    (out / "TST").mkdir(parents=True)
    (out / "TST" / "report.html").write_text("<html></html>")
    (out / "TST" / "series.csv").write_text("year,revenue\n1,100\n")
    monkeypatch.chdir(tmp_path)
    import subprocess, sys, shutil
    # Copy script into tmp workspace to mirror repo layout under tmp
    (tmp_path / "scripts").mkdir(exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]
    shutil.copy(repo_root / "scripts" / "make_index.py", tmp_path / "scripts" / "make_index.py")
    r = subprocess.run([sys.executable, str(tmp_path / "scripts" / "make_index.py")], capture_output=True, text=True)
    assert r.returncode == 0
    idx = out / "index.html"
    assert idx.exists()
    text = idx.read_text()
    assert "TST/report.html" in text and "TST/series.csv" in text
