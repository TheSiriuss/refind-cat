"""Repository paths shared by the art scripts (everything is relative to the repo root)."""
import os
from pathlib import Path
ROOT   = Path(__file__).resolve().parents[1]
ART    = ROOT / 'art'
WORK   = ART / 'work'                                   # intermediate files (git-ignored)
SOURCE = ART / 'source'
LAYERS = ART / 'layers'
DIST   = Path(os.environ.get('DIST', ROOT / 'dist'))   # the ready-to-copy ESP tree (DIST=... builds elsewhere)
THEME  = DIST / 'EFI' / 'refind' / 'themes' / 'cat'
WORK.mkdir(exist_ok=True)
