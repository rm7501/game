"""Render the five map dioramas (docs/previews/map_*.png). Needs the car GLBs from cars.py.

Run: python blender/render_dioramas.py [riyadh alula jeddah asir future]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))
import sr  # noqa: E402,F401
import kit_common  # noqa: E402


def riyadh():
    import kit_riyadh
    objs = kit_riyadh.build_all()
    objs += [kit_common.date_palm("SM_DatePalm_A", 9.0, 26, 1, 4.0), kit_common.date_palm("SM_DatePalm_B", 12.5, 28, 2, 7.0)]
    kit_riyadh.diorama(objs)


def alula():
    import kit_alula
    objs = kit_alula.build_all()
    extra = [kit_common.acacia(), kit_common.date_palm("SM_DatePalm_A", 9.0, 26, 1, 4.0),
             kit_common.date_palm("SM_DatePalm_C", 5.5, 22, 3, 2.0, dates=False)]
    kit_alula.diorama(objs, extra)


def jeddah():
    import kit_jeddah
    kit_jeddah.diorama(kit_jeddah.build_all())


def asir():
    import kit_asir
    kit_asir.diorama(kit_asir.build_all())


def future():
    import kit_future
    kit_future.diorama(kit_future.build_all())


MAPS = dict(riyadh=riyadh, alula=alula, jeddah=jeddah, asir=asir, future=future)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    for name in (argv or list(MAPS)):
        MAPS[name]()
