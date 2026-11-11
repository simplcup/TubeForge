"""End-to-end engine test: every format, cancellation, and queue recovery."""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.core import DownloadManager, Job, Settings

OUT = Path(os.environ["TEMP"]) / "tf_engine_test"
SHORT = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
LONG = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"

FORMATS = ["mp3", "flac", "wav", "opus", "m4a", "mp4"]
results = {}
failures = []
pending = {}
fmt_terminal = set()
phase = "formats"
manager = None
app = None
long_job = None
recovery_job = None
cancelled_long = False
_finished = False


def make_job(fmt):
    kind = "video" if fmt in ("mp4", "webm", "mkv") else "audio"
    return Job(url=SHORT, fmt=fmt, kind=kind, quality="360")


def on_started(job):
    print("START", job.fmt, job.id, flush=True)


def on_done(job):
    results[job.fmt] = (job.status, job.filepath, job.filesize)
    p = Path(job.filepath) if job.filepath else None
    ok = bool(p and p.exists() and p.suffix.lower() == f".{job.fmt}" and p.stat().st_size > 1000)
    print(f"DONE {job.fmt:4} ok={ok} size={job.filesize/1024:.0f}KB file={p.name if p else None}", flush=True)
    if not ok:
        failures.append(f"{job.fmt}: bad output {job.filepath}")
    if phase == "formats":
        fmt_terminal.add(job.fmt)
    if job is recovery_job:
        QTimer.singleShot(400, finish)


def on_failed(job_id, msg):
    fmt = pending.get(job_id)
    print("FAILED", fmt, msg[:300], flush=True)
    failures.append(f"{fmt}: {msg}")
    if phase == "formats" and fmt in FORMATS:
        fmt_terminal.add(fmt)
    if fmt == "recovery":
        QTimer.singleShot(400, finish)


def on_cancelled(job_id):
    global cancelled_long
    if long_job and job_id == long_job.id:
        cancelled_long = True
    print("CANCELLED", job_id, flush=True)


def start():
    global manager, phase, long_job
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    settings.data["output_dir"] = str(OUT)
    settings.data["embed_thumbnail"] = False
    settings.data["embed_metadata"] = True
    settings.data["force_ipv4"] = True
    manager = DownloadManager(settings)
    manager.job_started.connect(on_started)
    manager.job_done.connect(on_done)
    manager.job_failed.connect(on_failed)
    manager.job_cancelled.connect(on_cancelled)
    manager.log.connect(lambda m: None)
    manager.start()
    for fmt in FORMATS:
        job = make_job(fmt)
        pending[job.id] = fmt
        manager.enqueue(job)
    QTimer.singleShot(300, poll)


def poll():
    global phase, long_job, recovery_job
    if phase == "formats":
        if len(fmt_terminal) >= len(FORMATS):
            print("formats phase complete", flush=True)
            phase = "cancel"
            long_job = Job(url=LONG, fmt="mp4", kind="video", quality="1080")
            pending[long_job.id] = "cancel-test"
            manager.enqueue(long_job)
            QTimer.singleShot(2600, lambda: (print("requesting cancel", flush=True), manager.cancel(long_job.id)))
            QTimer.singleShot(7500, enqueue_recovery)
    QTimer.singleShot(300, poll)


def enqueue_recovery():
    global phase, recovery_job
    phase = "recovery"
    print("recovery phase (cancel flag must be reset)", flush=True)
    recovery_job = Job(url=SHORT, fmt="mp3", kind="audio", quality="best")
    pending[recovery_job.id] = "recovery"
    manager.enqueue(recovery_job)


def finish():
    global _finished
    if _finished:
        return
    _finished = True
    print("\nRESULTS", flush=True)
    for fmt in FORMATS:
        print(fmt, results.get(fmt), flush=True)
    print("CANCELLED_LONG", cancelled_long, flush=True)
    print("FILES", flush=True)
    for p in sorted(OUT.glob("*")):
        print(" ", p.name, p.stat().st_size, flush=True)
    print("FAILURES", failures, flush=True)
    if manager:
        manager.stop()
        manager.wait(3000)
    QTimer.singleShot(200, app.quit)


app = QApplication(sys.argv)
QTimer.singleShot(100, start)
QTimer.singleShot(600000, finish)
app.exec()
