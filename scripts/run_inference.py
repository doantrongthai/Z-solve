import sys
from pathlib import Path

root_directory = Path(__file__).resolve().parent.parent
src_directory = root_directory / "src"
if str(root_directory) not in sys.path:
    sys.path.insert(0, str(root_directory))
if str(src_directory) not in sys.path:
    sys.path.insert(0, str(src_directory))

from scripts.run_pipeline import main

if __name__ == "__main__":
    main()
