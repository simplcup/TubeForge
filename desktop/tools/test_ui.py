"""UI-level integration test: fetch -> choose format -> download -> history."""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_APPDATA = Path(tempfile.gettempdir()) / "tf_ui_appdata"
TEST_OUT = Path(tempfile.gettempdir()) / "tf_ui_output"
for p in (TEST_APPDATA, TEST_OUT):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)
os.environ["APPDATA"] = str(TEST_APPDATA)
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.theme import apply_theme
from app.window import MainWindow

SHORT = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


def wait_for(cond, seconds=120, label=""):
    loop = QEventLoop()
    deadline = time.time() + seconds
    timer = QTimer()
    timer.setInterval(100)

    def check():
        if cond() or time.time() > deadline:
            loop.quit()

    timer.timeout.connect(check)
    timer.start()
    check()
    if not cond():
        loop.exec()
    timer.stop()
    return bool(cond())


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.settings.set("output_dir", str(TEST_OUT))
    win.resize(1200, 860)
    win.show()
    QTest.qWait(300)

    home = win.home
    home.url_edit.setText(SHORT)
    home.fetch()
    ok = wait_for(lambda: home.meta is not None or home.error_label.isVisible(), 120, "fetch")
    if not home.meta:
        worker = home._fetch_worker
        print("FETCH FAILED. worker:", worker, "running:", bool(worker and worker.isRunning()),
              "error:", home.error_label.text(), flush=True)
        if worker and worker.isRunning():
            worker.terminate()
            worker.wait(2000)
        win.manager.stop()
        win.manager.wait(2000)
        raise SystemExit("metadata fetch failed")
    print("FETCH OK:", home.preview_title.text(), "|", home.preview_meta.text())

    # choose MP4 360p
    home.cards["mp4"].click()
    QTest.qWait(100)
    assert home.quality_combo.isEnabled(), "quality combo should enable for video"
    idx = home.quality_combo.findData("360")
    home.quality_combo.setCurrentIndex(idx)
    assert "MP4" in home.selection_label.text(), home.selection_label.text()
    print("SELECTION:", home.selection_label.text())

    # download
    assert home.download_btn.isEnabled(), "download button disabled"
    home.download_btn.click()
    QTest.qWait(300)
    assert len(win.queue.cards) == 1, "queue did not show queued job immediately"
    print("QUEUED CARD:", list(win.queue.cards.values())[0].status.text())

    ok = wait_for(lambda: bool(win.history.items), 240)
    if not ok:
        cards = list(win.queue.cards.values())
        print("QUEUE STATE:", [(c.job.status, c.job.error) for c in cards])
        print("ACTIVE CARD VISIBLE:", home.active_card.isVisible())
        raise SystemExit("download did not finish")
    QTest.qWait(700)

    entry = win.history.items[0]
    path = Path(entry["filepath"])
    print("HISTORY:", entry["title"], "|", entry["fmt"], "|", entry["quality"], "|", entry["filesize"])
    print("FILE EXISTS:", path.exists(), path)
    assert path.exists() and path.suffix == ".mp4" and path.stat().st_size > 1000

    queue_card = next(iter(win.queue.cards.values()))
    print("QUEUE STATUS:", queue_card.job.status, "|", queue_card.status.text())
    assert queue_card.job.status == "done"

    win.switch_page(1)
    QTest.qWait(300)
    win.grab().save(str(ROOT / "tools" / "shots" / "queue_real.png"))
    win.switch_page(2)
    QTest.qWait(300)
    win.grab().save(str(ROOT / "tools" / "shots" / "history_real.png"))
    win.switch_page(0)
    QTest.qWait(300)
    win.grab().save(str(ROOT / "tools" / "shots" / "download_real.png"))

    print("HISTORY COUNT:", len(win.history.items))
    print("TOAST VISIBLE:", win.toast.isVisible())
    win.close()
    QTest.qWait(400)
    print("UI TEST PASSED")
    shutil.rmtree(TEST_OUT, ignore_errors=True)
    shutil.rmtree(TEST_APPDATA, ignore_errors=True)


if __name__ == "__main__":
    main()
