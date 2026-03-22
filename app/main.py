import sys
import os
import warnings
from pathlib import Path

# Silence noisy library warnings that confuse users
warnings.filterwarnings("ignore", message=".*flash.*attn.*")
warnings.filterwarnings("ignore", message=".*flash-attn.*")
os.environ["TRANSFORMERS_NO_FLASH_ATTN_WARNING"] = "1"

# Ensure app package is importable when run as `python -m app.main`
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.gui.app_window import AppWindow


def main():
    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
