import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent / ".agents" / "skills" / "story-engine" / "tools"
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(TOOLS_DIR / "lib"))
sys.path.insert(0, str(TOOLS_DIR / "phases"))
