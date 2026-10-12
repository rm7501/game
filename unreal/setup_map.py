"""Sahara Racers - lighting presets + kit showcase for each map (run inside the UE5 editor).

Usage (Tools > Execute Python Script, or the Output Log in Python mode):
    exec(open(r"C:/path/to/game/unreal/setup_map.py").read())
    setup("riyadh")                 # lighting preset only, in the currently open level
    setup("alula", showcase=True)   # + lay out every AlUla asset in a row at the origin
Maps: riyadh | alula | jeddah | asir | future

The preset creates (or reuses) one each of: DirectionalLight, SkyAtmosphere, SkyLight,
ExponentialHeightFog, VolumetricCloud (optional) and an unbound PostProcessVolume, all tagged "SR_Lighting".
Values are a starting point tuned for the look in docs/previews; adjust to taste.
"""
import unreal

DEST = "/Game/SaharaRacers"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary

PRESETS = {
    # sun pitch (deg below horizon is negative elevation), yaw, lux, colour temperature (K),
    # fog density, fog colour, volumetric fog, clouds, exposure range (EV100), bloom
    "riyadh": dict(pitch=-35, yaw=200, lux=0.4, temp=8500, sky_int=0.35, fog=0.012, fog_col=(0.16, 0.08, 0.07),
                   vol_fog=True, clouds=False, ev=(-1.5, 3.0), bloom=1.4, note="Night: moonlight + city glow"),
    "alula": dict(pitch=-7, yaw=250, lux=8.0, temp=3600, sky_int=1.0, fog=0.006, fog_col=(0.55, 0.35, 0.2),
                  vol_fog=False, clouds=False, ev=(9.0, 13.0), bloom=0.8, note="Golden hour in the sandstone valley"),
    "jeddah": dict(pitch=-4, yaw=260, lux=6.0, temp=3200, sky_int=1.0, fog=0.02, fog_col=(0.6, 0.4, 0.3),
                   vol_fog=True, clouds=True, ev=(7.0, 12.0), bloom=1.0, note="Red Sea sunset, humid haze, lanterns"),
    "asir": dict(pitch=-18, yaw=120, lux=9.0, temp=5400, sky_int=1.2, fog=0.05, fog_col=(0.75, 0.8, 0.88),
                 vol_fog=True, clouds=True, ev=(9.0, 14.0), bloom=0.6, note="Misty highland morning"),
    "future": dict(pitch=-3, yaw=110, lux=1.5, temp=9500, sky_int=0.6, fog=0.01, fog_col=(0.2, 0.25, 0.45),
                   vol_fog=True, clouds=False, ev=(1.0, 6.0), bloom=1.6, note="Blue hour inside The Line"),
}

TAG = "SR_Lighting"


def _find_or_spawn(cls, label):
    for a in eas.get_all_level_actors():
        if isinstance(a, cls) and TAG in [str(t) for t in a.tags]:
            return a
    a = eas.spawn_actor_from_class(cls, unreal.Vector(0, 0, 300), unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.set_editor_property("tags", [unreal.Name(TAG)])
    return a


def _set(obj, **props):
    for k, v in props.items():
        try:
            obj.set_editor_property(k, v)
        except Exception as ex:  # noqa: BLE001  (property names differ slightly between UE versions)
            unreal.log_warning(f"[SaharaRacers] {obj.get_name()}.{k}: {ex}")


def apply_preset(name):
    p = PRESETS[name]
    sun = _find_or_spawn(unreal.DirectionalLight, "SR_Sun")
    sun.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=float(p["pitch"]), yaw=float(p["yaw"])), False)
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    lc.set_intensity(p["lux"])
    _set(lc, use_temperature=True, temperature=float(p["temp"]), atmosphere_sun_light=True,
         cast_shadows=True, mobility=unreal.ComponentMobility.MOVABLE)

    _find_or_spawn(unreal.SkyAtmosphere, "SR_SkyAtmosphere")

    sky = _find_or_spawn(unreal.SkyLight, "SR_SkyLight")
    sc = sky.get_component_by_class(unreal.SkyLightComponent)
    _set(sc, real_time_capture=True, mobility=unreal.ComponentMobility.MOVABLE)
    sc.set_intensity(p["sky_int"])

    fog = _find_or_spawn(unreal.ExponentialHeightFog, "SR_HeightFog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    c = p["fog_col"]
    _set(fc, fog_density=p["fog"], fog_height_falloff=0.12, enable_volumetric_fog=p["vol_fog"])
    try:
        fc.set_fog_inscattering_color(unreal.LinearColor(c[0], c[1], c[2], 1))
    except Exception:
        _set(fc, fog_inscattering_luminance=unreal.LinearColor(c[0], c[1], c[2], 1))

    if p["clouds"]:
        _find_or_spawn(unreal.VolumetricCloud, "SR_Clouds")

    ppv = _find_or_spawn(unreal.PostProcessVolume, "SR_PostProcess")
    _set(ppv, unbound=True)
    s = ppv.get_editor_property("settings")
    for k, v in (("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", p["ev"][0]),
                 ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", p["ev"][1]),
                 ("override_bloom_intensity", True), ("bloom_intensity", p["bloom"]),
                 ("override_vignette_intensity", True), ("vignette_intensity", 0.35)):
        try:
            s.set_editor_property(k, v)
        except Exception:
            pass
    ppv.set_editor_property("settings", s)
    unreal.log(f"[SaharaRacers] preset '{name}' applied - {p['note']}")


def showcase(kit, origin=(0.0, 0.0, 0.0), gap_cm=2000.0):
    """Spawn every static mesh of a kit in a row (handy for browsing / screenshots)."""
    folder = f"{DEST}/{kit.capitalize()}"
    x = origin[0]
    for path in sorted(eal.list_assets(folder, recursive=False)):
        a = eal.load_asset(path)
        if not isinstance(a, unreal.StaticMesh):
            continue
        b = a.get_bounding_box()
        size = (b.max.x - b.min.x)
        actor = eas.spawn_actor_from_object(a, unreal.Vector(x - b.min.x, origin[1], origin[2]), unreal.Rotator(0, 0, 0))
        actor.set_folder_path(f"SaharaRacers/{kit}")
        x += size + gap_cm
    unreal.log(f"[SaharaRacers] showcase for {kit} spawned")


_spawn_showcase = showcase


def setup(name, showcase=False):
    """Apply the lighting preset for `name`; optionally lay out the kit's assets."""
    apply_preset(name)
    if showcase:
        _spawn_showcase(name)


unreal.log("[SaharaRacers] setup_map loaded: call setup('riyadh'|'alula'|'jeddah'|'asir'|'future', showcase=True)")
