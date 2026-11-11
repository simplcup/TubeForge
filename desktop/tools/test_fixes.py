"""Focused regression checks for the three reported bugs."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from app import theme, widgets
from app.core import Job
from app.pages import QueuePage
from app.widgets import GlowProgress, JobCard

OUT = ROOT / "tools" / "shots"
OUT.mkdir(exist_ok=True)


def check_progress_stripes(app: QApplication) -> GlowProgress:
    bar = GlowProgress(10)
    bar.resize(600, 10)
    bar.setValue(58)
    bar.setActive(True)
    bar.show()
    app.processEvents()
    path = OUT / "progress_fix.png"
    assert bar.grab().save(str(path)), "could not save progress shot"
    print(f"progress: {path}")
    return bar


def check_queue_done_action() -> JobCard:
    job = Job(url="x", fmt="opus", kind="audio", quality="best")
    job.status = "done"
    job.filepath = str(Path(os.environ["TEMP"]) / "tf_fix" / "track.opus")
    card = JobCard(job)
    actions = []
    card.action_requested.connect(lambda jid, action: actions.append(action))
    card._on_action()
    assert actions == ["folder"], actions
    print("queue card: done -> folder")
    return card


def check_queue_download_size(app: QApplication) -> None:
    job = Job(url="x", fmt="mp3", kind="audio", quality="best", duration=558)
    job.title = "The Most Powerful Smartphone (2026) – REDMAGIC 12 Pro"
    job.status = "downloading"
    job.progress = 50.0
    job.downloaded = 11_000_000
    job.total = 22_000_000
    job.total_estimated = True
    card = JobCard(job)
    text = card.meta.text()
    assert "~21.0 MB" in text, text
    card.resize(720, 100)
    card.show()
    app.processEvents()
    path = OUT / "queue_size.png"
    assert card.grab().save(str(path)), "could not save queue size shot"
    job.total_estimated = False
    card.update_job(job)
    assert "~" not in card.meta.text(), card.meta.text()
    card.close()
    print(f"queue card shows estimated final size ok: {path}")


def check_folder_handler() -> None:
    calls = []
    original_folder, original_file = widgets.open_folder, widgets.open_path
    widgets.open_folder = lambda path: calls.append(("folder", path))
    widgets.open_path = lambda path: calls.append(("file", path))
    try:
        job = Job(url="x", fmt="mp3", kind="audio", quality="best")
        job.status = "done"
        job.filepath = str(Path(os.environ["TEMP"]) / "tf_fix" / "track.mp3")
        card = SimpleNamespace(job=job)
        fake = SimpleNamespace(
            cards={job.id: card},
            settings=SimpleNamespace(data={"output_dir": str(Path(os.environ["TEMP"]))}),
        )
        QueuePage._on_action(fake, job.id, "folder")
    finally:
        widgets.open_folder, widgets.open_path = original_folder, original_file
    assert calls == [("folder", job.filepath)], calls
    print("queue handler: opens containing folder only")


def main() -> int:
    app = QApplication(sys.argv)
    theme.apply_theme(app, "midnight")
    bar = check_progress_stripes(app)
    card = check_queue_done_action()
    check_queue_download_size(app)
    check_folder_handler()
    bar.setActive(False)
    bar.close()
    card.close()
    bar.deleteLater()
    card.deleteLater()
    app.processEvents()
    print("all fix checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
