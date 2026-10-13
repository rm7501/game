"""Sahara Racers - assemble a complete race map in the open Unreal level from assets/maps/<Map>/.

Run AFTER unreal/import_assets.py (kits, textures and material instances must exist).
  1. File > New Level > Empty Level (save it, e.g. /Game/SaharaRacers/Maps/L_AlUla)
  2. Output Log, Python mode:
        exec(open(r"C:/path/to/game/unreal/build_map.py").read())
        build("AlUla")
Maps: RiyadhNights | AlUla | JeddahCorniche | AsirMountains | FutureCity

What build() does (everything lands in Outliner folders SaharaRacers/<Map>/...):
  * imports the map folder -> /Game/SaharaRacers/Maps/<Map>/
        SM_<Map>_Terrain_<r>_<c>  Nanite terrain tiles (vertex-colour layer blend, M_SR_TerrainBlend)
        SM_<Map>_<Track>_NN       road chunks: asphalt, kerbs, barriers, bridges, tunnels (complex collision)
        SM_<Map>_Water            sea / lake plane (no collision, tag SR_Water)
        SM_<Map>_Backdrop         scenery ring from the map edge to the horizon (~24 km), same terrain material
        SM_<Map>_Far_*            merged distant city / forest / skyline meshes (no collision)
        props/*.fbx               map-specific landmarks (-> .../Maps/<Map>/Props)
  * spawns every prop listed in layout.json (kit meshes from /Game/SaharaRacers/<Kit>/)
  * gameplay from track.json (tags let Blueprints find them with GetAllActorsWithTag):
        PlayerStart x8         tags SR_Grid, SR_Grid_<slot>
        TriggerBox per checkpoint   tags SR_Checkpoint, SR_CP_<index>   (index 0 = start/finish line)
        card pickups / boost pads   SM_CardPickup / SM_BoostPad (or your Blueprints, see ITEM_CLASSES)
        TargetPoints every 20 m along the racing line (SR_Line, SR_Line_<n>) and each shortcut
        (SR_Shortcut, SR_<ShortcutName>, SR_<ShortcutName>_<n>, plus SR_Hidden for secret ones) - AI waypoints
  * applies the lighting preset from setup_map.py

Landscape instead of mesh tiles: build("AlUla", terrain="none") skips the tiles; then import
assets/maps/<Map>/landscape/H_<Map>.png in Landscape mode with the numbers printed by landscape_help().
Re-running build() first deletes the actors it spawned before (tag SR_Map_<Map>).
"""
import importlib.util
import json
import os

import unreal

try:
    REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:   # exec() from the console has no __file__
    REPO = r"C:/Users/rayan/OneDrive/Desktop/game"          # <-- set to your clone of this repo
DEST = "/Game/SaharaRacers"
MAPS = {"RiyadhNights": "riyadh", "AlUla": "alula", "JeddahCorniche": "jeddah", "AsirMountains": "asir",
        "FutureCity": "future"}
# Optional: your own Blueprint classes for gameplay items (else the kit meshes are spawned as markers)
ITEM_CLASSES = {"card": None, "boost": None, "checkpoint": None}   # e.g. "/Game/Blueprints/BP_CardPickup.BP_CardPickup_C"
WAYPOINT_EVERY_M = 20.0

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, "unreal", filename))
    mod = importlib.util.module_from_spec(spec)
    mod.REPO = REPO
    spec.loader.exec_module(mod)
    return mod


imp = _load_module("sr_import_assets", "import_assets.py")
lighting = _load_module("sr_setup_map", "setup_map.py")


def log(msg):
    unreal.log(f"[SaharaRacers] {msg}")


# ------------------------------------------------------------------ import ---
def kit_folder(kit):
    if kit.startswith("maps/"):
        parts = kit.split("/")              # maps/<Map>/props
        return f"{DEST}/Maps/{parts[1]}/Props"
    return f"{DEST}/{kit.capitalize()}"


def import_map_assets(map_name):
    imp.force_legacy_fbx()
    instances, manifest = imp.build_instances()
    src = os.path.join(REPO, "assets", "maps", map_name)
    dest = f"{DEST}/Maps/{map_name}"
    jobs = [(os.path.join(src, f), dest) for f in sorted(os.listdir(src)) if f.lower().endswith(".fbx")]
    props = os.path.join(src, "props")
    if os.path.isdir(props):
        jobs += [(os.path.join(props, f), f"{dest}/Props") for f in sorted(os.listdir(props)) if f.lower().endswith(".fbx")]
    meshes = {}
    with unreal.ScopedSlowTask(len(jobs), f"Sahara Racers: importing {map_name}") as task:
        task.make_dialog(True)
        for path, folder in jobs:
            if task.should_cancel():
                break
            task.enter_progress_frame(1, os.path.basename(path))
            for a in import_static(path, folder, vertex_colors=any(k in os.path.basename(path) for k in ("_Terrain_", "_Backdrop"))):
                if not isinstance(a, unreal.StaticMesh):
                    continue
                imp.assign_materials(a, instances, manifest)
                if not a.get_name().endswith("_Water") and "_Far_" not in a.get_name():
                    imp.complex_collision(a)
                meshes[a.get_name()] = a
    log(f"{map_name}: imported {len(meshes)} meshes")
    return meshes


def import_static(path, folder, vertex_colors=False):
    """Static mesh import; terrain tiles keep their vertex colours (= the layer blend weights)."""
    ui = imp.fbx_options(False)
    if vertex_colors:
        sm = ui.get_editor_property("static_mesh_import_data")
        try:
            sm.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
        except Exception as ex:  # noqa: BLE001
            unreal.log_warning(f"[SaharaRacers] vertex colour option: {ex}")
    t = unreal.AssetImportTask()
    for k, v in (("filename", path), ("destination_path", folder), ("automated", True), ("replace_existing", True),
                 ("save", True), ("options", ui)):
        t.set_editor_property(k, v)
    imp.tools.import_asset_tasks([t])
    return [eal.load_asset(p) for p in t.get_editor_property("imported_object_paths")]


# ------------------------------------------------------------------- spawn ---
def _tag_actor(a, map_name, folder, label=None, extra=()):
    tags = [unreal.Name(f"SR_Map_{map_name}")] + [unreal.Name(t) for t in extra]
    a.set_editor_property("tags", tags)
    a.set_folder_path(f"SaharaRacers/{map_name}/{folder}")
    if label:
        a.set_actor_label(label)


def clear_map(map_name):
    tag = f"SR_Map_{map_name}"
    n = 0
    for a in eas.get_all_level_actors():
        if tag in [str(t) for t in a.tags]:
            eas.destroy_actor(a)
            n += 1
    if n:
        log(f"removed {n} actors from a previous build of {map_name}")


def spawn_mesh(mesh, loc, yaw=0.0, scale=1.0):
    a = eas.spawn_actor_from_object(mesh, unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=0.0, yaw=float(yaw)))
    if a and scale != 1.0:
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    return a


def spawn_class(path, loc, yaw=0.0):
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path.rsplit(".", 1)[0]) if path else None
    if not cls:
        return None
    return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=0.0, yaw=float(yaw)))


def spawn_world(map_name, meshes, terrain=True):
    n = 0
    for name, mesh in sorted(meshes.items()):
        if "/Props/" in mesh.get_path_name():
            continue
        is_terrain = "_Terrain_" in name
        if is_terrain and not terrain:
            continue
        a = spawn_mesh(mesh, (0, 0, 0))
        if not a:
            continue
        sub = ("Terrain" if is_terrain else "Water" if name.endswith("_Water") else
               "Backdrop" if ("_Backdrop" in name or "_Far_" in name) else "Track")
        tags = {"Water": ["SR_Water"], "Track": ["SR_Road"], "Terrain": ["SR_Terrain"], "Backdrop": ["SR_Backdrop"]}[sub]
        _tag_actor(a, map_name, sub, name, tags)
        if sub == "Water" or "_Far_" in name:
            a.set_actor_enable_collision(False)
        n += 1
    log(f"{map_name}: {n} terrain / track / water actors")


def spawn_layout(map_name):
    with open(os.path.join(REPO, "assets", "maps", map_name, "layout.json")) as f:
        layout = json.load(f)
    cache, missing, n = {}, set(), 0
    props = layout["props"]
    with unreal.ScopedSlowTask(len(props), f"Sahara Racers: placing {len(props)} props") as task:
        task.make_dialog(True)
        for p in props:
            if task.should_cancel():
                break
            task.enter_progress_frame(1)
            key = (p["kit"], p["asset"])
            if key not in cache:
                path = f"{kit_folder(p['kit'])}/{p['asset']}"
                cache[key] = eal.load_asset(path) if eal.does_asset_exist(path) else None
            mesh = cache[key]
            if mesh is None:
                missing.add(f"{p['kit']}/{p['asset']}")
                continue
            a = spawn_mesh(mesh, (p["x"], p["y"], p["z"]), p["yaw"], p["scale"])
            if a:
                _tag_actor(a, map_name, f"Props/{p['kit'].split('/')[-1].capitalize()}/{p['asset']}", extra=("SR_Prop",))
                if p["asset"].startswith(imp.NO_COLLISION_PREFIXES):     # birds, flags, bunting, grass...
                    a.set_actor_enable_collision(False)
                n += 1
    log(f"{map_name}: {n} props placed")
    if missing:
        unreal.log_warning(f"[SaharaRacers] missing (run import_assets.py first?): {sorted(missing)}")


def spawn_gameplay(map_name):
    with open(os.path.join(REPO, "assets", "maps", map_name, "track.json")) as f:
        tr = json.load(f)
    # start grid
    for g in tr["start_grid"]:
        a = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(g["x"], g["y"], g["z"] + 60),
                                       unreal.Rotator(roll=0.0, pitch=0.0, yaw=g["yaw"]))
        _tag_actor(a, map_name, "Gameplay/Grid", f"SR_Grid_{g['slot']}", ("SR_Grid", f"SR_Grid_{g['slot']}"))
    # checkpoints: trigger boxes across the road
    for c in tr["checkpoints"]:
        loc = (c["x"], c["y"], c["z"] + 400)
        a = spawn_class(ITEM_CLASSES.get("checkpoint"), loc, c["yaw"]) or \
            eas.spawn_actor_from_class(unreal.TriggerBox, unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=0.0, yaw=c["yaw"]))
        comp = a.get_component_by_class(unreal.BoxComponent)
        if comp:
            ext = unreal.Vector(300.0, c["width_cm"] / 2.0, 800.0)
            try:
                comp.set_box_extent(ext, True)
            except Exception:
                comp.set_editor_property("box_extent", ext)
        _tag_actor(a, map_name, "Gameplay/Checkpoints", f"SR_CP_{c['index']:02d}", ("SR_Checkpoint", f"SR_CP_{c['index']}"))
    # card pickups and boost pads
    card = eal.load_asset(f"{DEST}/Common/SM_CardPickup") if eal.does_asset_exist(f"{DEST}/Common/SM_CardPickup") else None
    boost = eal.load_asset(f"{DEST}/Common/SM_BoostPad") if eal.does_asset_exist(f"{DEST}/Common/SM_BoostPad") else None
    for it in tr["items"]:
        loc = (it["x"], it["y"], it["z"])
        kind = it["type"]
        a = spawn_class(ITEM_CLASSES.get(kind), loc, it["yaw"])
        if a is None:
            mesh = card if kind == "card" else boost
            a = spawn_mesh(mesh, loc, it["yaw"]) if mesh else None
        if a:
            tag = "SR_CardPickup" if kind == "card" else "SR_BoostPad"
            _tag_actor(a, map_name, f"Gameplay/{'Cards' if kind == 'card' else 'Boosts'}", extra=(tag,))
    # waypoints along the racing line and every shortcut (AI, minimap, wrong-way detection)
    def waypoints(samples, folder, base_tags, prefix):
        last, k = -1e9, 0
        for smp in samples:
            if smp["s"] - last < WAYPOINT_EVERY_M or smp.get("air"):
                continue
            last = smp["s"]
            a = eas.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(smp["x"], smp["y"], smp["z"] + 100),
                                           unreal.Rotator(roll=0.0, pitch=0.0, yaw=smp["yaw"]))
            _tag_actor(a, map_name, folder, f"{prefix}_{k:03d}", base_tags + (f"{prefix}_{k}",))
            k += 1
        return k
    n = waypoints(tr["main"], "Gameplay/RacingLine", ("SR_Line",), "SR_Line")
    for sc in tr["shortcuts"]:
        extra = ("SR_Shortcut", f"SR_{sc['name']}") + (("SR_Hidden",) if sc["hidden"] else ())
        waypoints(sc["samples"], f"Gameplay/Shortcuts/{sc['name']}", extra, f"SR_{sc['name']}")
    log(f"{map_name}: grid, {len(tr['checkpoints'])} checkpoints, {len(tr['items'])} items, {n} racing-line waypoints, "
        f"{len(tr['shortcuts'])} shortcuts")


def landscape_help(map_name):
    """Print the numbers for importing the heightmap as a UE Landscape (alternative to the mesh tiles)."""
    with open(os.path.join(REPO, "assets", "maps", map_name, "landscape", "landscape.json")) as f:
        L = json.load(f)
    folder = os.path.join(REPO, "assets", "maps", map_name, "landscape")
    log(f"Landscape for {map_name}: Landscape mode > Manage > New > Import from File")
    log(f"  Heightmap: {os.path.join(folder, L['heightmap'])}   (resolution {L['resolution']} x {L['resolution']})")
    log(f"  Location (cm): {L['ue_location_cm']}   Scale: {L['ue_scale']}")
    log(f"  Layers: {L['layers']} -> weightmaps {L['weightmaps']}")
    if L.get("water_level_m") is not None:
        log(f"  Water plane at {L['water_level_m'] * 100:.0f} cm")
    return L


def build(map_name, terrain="tiles", props=True, gameplay=True, light=True):
    """Import + assemble a map in the current level. terrain: 'tiles' (Nanite mesh) or 'none' (use a Landscape)."""
    if map_name not in MAPS:
        raise ValueError(f"unknown map {map_name}; choose from {list(MAPS)}")
    clear_map(map_name)
    meshes = import_map_assets(map_name)
    spawn_world(map_name, meshes, terrain=(terrain == "tiles"))
    if props:
        spawn_layout(map_name)
    if gameplay:
        spawn_gameplay(map_name)
    if light:
        lighting.apply_preset(MAPS[map_name])
    if terrain != "tiles":
        landscape_help(map_name)
    log(f"{map_name} built. Save the level (Ctrl+S). Minimap: assets/maps/{map_name}/minimap.png")


log("build_map loaded: build('RiyadhNights' | 'AlUla' | 'JeddahCorniche' | 'AsirMountains' | 'FutureCity')")
