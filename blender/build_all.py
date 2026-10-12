"""Rebuild the whole Sahara Racers asset pack from source.

  python blender/build_all.py                 (bpy from PyPI:  pip install bpy==5.2.2 pillow arabic-reshaper python-bidi)
  blender -b -P blender/build_all.py          (Blender 5.x; textures/cards are skipped if Pillow is missing -
                                               the committed PNG/JPGs are reused)
Steps: textures -> common props -> 8 cars (FBX + rig + previews) -> 5 map kits -> card art -> map dioramas.
Add --no-render to skip all Cycles renders (much faster).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
render = "--no-render" not in sys.argv


def run(*args):
    print(">>", " ".join(args), flush=True)
    subprocess.check_call([PY, *args], cwd=os.path.dirname(HERE))


try:
    import numpy, PIL, scipy  # noqa: F401,E401
    run(os.path.join(HERE, "lib", "textures.py"))
except ImportError:
    print("numpy/Pillow/scipy missing: reusing committed textures")
run(os.path.join(HERE, "kit_common.py"), *([] if render else ["--no-render"]))
run(os.path.join(HERE, "cars.py"), *([] if render else ["--no-render"]))
for kit in ("riyadh", "alula", "jeddah", "asir", "future"):
    run(os.path.join(HERE, f"kit_{kit}.py"))
try:
    import PIL  # noqa: F401
    run(os.path.join(HERE, "card_art.py"))
except ImportError:
    pass
if render:
    run(os.path.join(HERE, "render_dioramas.py"))
