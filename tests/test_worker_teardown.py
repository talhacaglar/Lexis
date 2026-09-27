"""Owner teardown must never delete a running QThread."""

import os
import subprocess
import sys
import textwrap


def test_deleting_owner_waits_for_all_running_workers():
    # An isolated process turns a Qt abort into a regular test failure.
    script = textwrap.dedent("""\
        import resource
        import time
        from PyQt6.QtCore import QCoreApplication, QEvent
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtTest import QTest
        from lexis.workers.ai_worker import AIGenerationWorker

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        app = QApplication([])
        owner = QWidget()
        completed = []
        class FakeAIService:
            def generate_word_data(self, term, language):
                time.sleep(0.15)
                completed.append(True)
                return {}
        workers = [AIGenerationWorker(FakeAIService(), 'test', parent=owner) for _ in range(2)]
        for worker in workers:
            worker.start()
        QTest.qWait(10)
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert len(completed) == 2
        print('owner teardown completed')
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "owner teardown completed" in result.stdout
