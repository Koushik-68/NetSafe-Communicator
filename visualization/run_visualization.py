import os
import sys


# Ensure project root is on sys.path so package imports work from any cwd.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from visualization.app import main


if __name__ == "__main__":
    main()
