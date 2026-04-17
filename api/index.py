import sys
from pathlib import Path

# Ensure the project root is on the Python path so `main` can be imported
# regardless of how Vercel sets up the function's working directory.
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app as app  # noqa: E402, F401
