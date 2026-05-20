from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from gamebot.ui.app import GameBotWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("GameBot")
    window = GameBotWindow()
    window.resize(1280, 820)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
