import sys
from pathlib import Path

# Ensure project root is on sys.path so test modules can import package modules normally
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
