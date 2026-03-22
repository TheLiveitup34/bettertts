import sys
from pathlib import Path

# Ensure app package is importable when run as `python -m app.main`
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.gui.app_window import AppWindow


def main():
    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
