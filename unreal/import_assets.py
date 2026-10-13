"""Sahara Racers - import every asset from this repo into an Unreal Engine 5 project.

HOW TO RUN (UE 5.1 - 5.6):
  1. Edit > Plugins: enable "Python Editor Script Plugin" (and restart).
  2. Tools > Execute Python Script...  ->  pick this file (unreal/import_assets.py).
     (or in the Output Log, switch "Cmd" to "Python" and run:
      exec(open(r"C:/path/to/game/unreal/import_assets.py").read())   after setting REPO below)

WHAT IT DOES
  * imports all textures (normal maps flipped OpenGL -> DirectX, masks linear)
  * builds master materials in /Game/SaharaRacers/Materials:
        M_SR_Master   (opaque PBR: BaseTex*Tint, NormalTex, RoughTex*Roughness, Metallic, emissive)
        M_SR_CarPaint (clear-coat version for car bodies)
        M_SR_Glass    (translucent)
        M_SR_Foliage  (two-sided: palm fronds, awnings, flags)
        M_SR_VFX      (additive, unlit: ability effects)
        M_SR_TerrainBlend (map terrain tiles: 4 texture sets blended by vertex colour R/G/B)
        M_SR_Water    (sea / lake: two panning wave normals)
  * creates one Material Instance per material in assets/materials.json (MI_<Name>)
  * imports every FBX:
        assets/<kit>/SM_*.fbx         -> /Game/SaharaRacers/<Kit>/          (Nanite on, collision)
        assets/cars/<Car>/SK_<Car>.fbx -> /Game/SaharaRacers/Cars/<Car>/    (skeletal + physics asset)
        assets/cars/<Car>/SM_*.fbx     -> /Game/SaharaRacers/Cars/<Car>/    (static body + wheels)
  * assigns the material instances to every mesh slot by name
Re-running is safe: existing assets are re-imported / updated in place.
"""
import json
import os

import unreal

# ------------------------------------------------------------------ config ---
try:
    REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:   # exec() from the console has no __file__
    REPO = r"C:/Users/rayan/OneDrive/Desktop/game"          # <-- set to your clone of this repo
DEST = "/Game/SaharaRacers"
KITS = ["common", "riyadh", "alula", "jeddah", "asir", "future", "life"]
IMPORT_CARS = True
USE_NANITE = True

ASSETS = os.path.join(REPO, "assets")
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log(f"[SaharaRacers] {msg}")


def force_legacy_fbx():
    """UE 5.5+ routes FBX through Interchange, which ignores FbxImportUI. Use the classic importer."""
    for cvar in ("Interchange.FeatureFlags.Import.FBX", "Interchange.FeatureFlags.Import.FBX.ToLevel"):
        try:
            unreal.SystemLibrary.execute_console_command(None, f"{cvar} false")
        except Exception:
            pass


# ---------------------------------------------------------------- textures ---
def import_files(files, dest):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", f)
        t.set_editor_property("destination_path", dest)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", True)
        tasks.append(t)
    if tasks:
        tools.import_asset_tasks(tasks)
    out = []
    for t in tasks:
        out += list(t.get_editor_property("imported_object_paths"))
    return out


def configure_texture(path):
    tex = eal.load_asset(path)
    if not tex:
        return
    name = path.split("/")[-1].split(".")[0]
    if name.endswith("_N"):
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("flip_green_channel", True)     # Blender/OpenGL -> Unreal/DirectX
    elif name.endswith("_R"):
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    eal.save_loaded_asset(tex)


def import_textures():
    folders = [(os.path.join(ASSETS, "textures"), f"{DEST}/Textures")]
    for kit in KITS + ["cars"]:
        p = os.path.join(ASSETS, kit, "textures")
        if os.path.isdir(p):
            folders.append((p, f"{DEST}/Textures/{kit.capitalize()}"))
    for src, dest in folders:
        files = [os.path.join(src, f) for f in sorted(os.listdir(src)) if f.lower().endswith((".png", ".jpg"))]
        for p in import_files(files, dest):
            configure_texture(p)
        log(f"textures: {len(files)} from {os.path.relpath(src, REPO)}")


def tex_asset(name):
    """Find an imported texture by base name anywhere under /Game/SaharaRacers/Textures."""
    for sub in [""] + ["/" + k.capitalize() for k in KITS + ["cars"]]:
        p = f"{DEST}/Textures{sub}/{name}"
        if eal.does_asset_exist(p):
            return eal.load_asset(p)
    return None


# ---------------------------------------------------------------- materials ---
def new_asset(name, folder, cls, factory):
    path = f"{folder}/{name}"
    if eal.does_asset_exist(path):
        return eal.load_asset(path), False
    return tools.create_asset(name, folder, cls, factory), True


def build_master(name, clear_coat=False, two_sided=False, translucent=False, vfx=False):
    folder = f"{DEST}/Materials"
    m, created = new_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return m
    white = tex_asset("T_Default_D")
    flat = tex_asset("T_Default_N")
    mask = tex_asset("T_Default_R")
    X = mel.create_material_expression

    def E(cls, x, y):
        return X(m, cls, x, y)

    def scalar(pname, val, x, y):
        e = E(unreal.MaterialExpressionScalarParameter, x, y)
        e.set_editor_property("parameter_name", pname)
        e.set_editor_property("default_value", val)
        return e

    def vector(pname, val, x, y):
        e = E(unreal.MaterialExpressionVectorParameter, x, y)
        e.set_editor_property("parameter_name", pname)
        e.set_editor_property("default_value", unreal.LinearColor(*val))
        return e

    def texture(pname, tex, x, y, sampler):
        e = E(unreal.MaterialExpressionTextureSampleParameter2D, x, y)
        e.set_editor_property("parameter_name", pname)
        if tex:
            e.set_editor_property("texture", tex)
        e.set_editor_property("sampler_type", sampler)
        return e

    def mul(a, ao, b, bo, x, y):
        e = E(unreal.MaterialExpressionMultiply, x, y)
        mel.connect_material_expressions(a, ao, e, "A")
        mel.connect_material_expressions(b, bo, e, "B")
        return e

    P = unreal.MaterialProperty
    S = unreal.MaterialSamplerType
    if two_sided:
        m.set_editor_property("two_sided", True)
    if vfx:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        col = vector("EmissiveColor", (1, 1, 1, 1), -800, 0)
        st = scalar("EmissiveStrength", 5.0, -800, 200)
        op = scalar("Opacity", 0.6, -800, 300)
        e1 = mul(col, "", st, "", -500, 100)
        e2 = mul(e1, "", op, "", -300, 100)
        mel.connect_material_property(e2, "", P.MP_EMISSIVE_COLOR)
        mel.recompile_material(m)
        eal.save_loaded_asset(m)
        return m
    if translucent:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        try:
            m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        except Exception:
            pass
    if clear_coat:
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    # UVs (Blender already wrote UVs in texture-tile units, so UVScale defaults to 1)
    uv = E(unreal.MaterialExpressionTextureCoordinate, -1600, 0)
    uvs = scalar("UVScale", 1.0, -1600, 120)
    uvm = mul(uv, "", uvs, "", -1400, 40)
    base = texture("BaseTex", white, -1100, -500, S.SAMPLERTYPE_COLOR)
    nrm = texture("NormalTex", flat, -1100, -150, S.SAMPLERTYPE_NORMAL)
    rgh = texture("RoughTex", mask, -1100, 200, S.SAMPLERTYPE_MASKS)
    emt = texture("EmissiveTex", white, -1100, 550, S.SAMPLERTYPE_COLOR)
    for t in (base, nrm, rgh, emt):
        mel.connect_material_expressions(uvm, "", t, "UVs")
    tint = vector("Tint", (1, 1, 1, 1), -800, -400)
    mel.connect_material_property(mul(base, "RGB", tint, "", -500, -450), "", P.MP_BASE_COLOR)
    mel.connect_material_property(nrm, "RGB", P.MP_NORMAL)
    rs = scalar("Roughness", 0.5, -800, 260)
    mel.connect_material_property(mul(rgh, "R", rs, "", -500, 220), "", P.MP_ROUGHNESS)
    mel.connect_material_property(scalar("Metallic", 0.0, -500, 0), "", P.MP_METALLIC)
    ec = vector("EmissiveColor", (1, 1, 1, 1), -800, 650)
    es = scalar("EmissiveStrength", 0.0, -800, 780)
    e1 = mul(emt, "RGB", ec, "", -500, 600)
    mel.connect_material_property(mul(e1, "", es, "", -300, 650), "", P.MP_EMISSIVE_COLOR)
    if translucent:
        mel.connect_material_property(scalar("Opacity", 0.35, -500, 900), "", P.MP_OPACITY)
    if clear_coat:
        mel.connect_material_property(scalar("ClearCoat", 1.0, -500, 1000), "", P.MP_CUSTOM_DATA0)
        mel.connect_material_property(scalar("ClearCoatRoughness", 0.03, -500, 1100), "", P.MP_CUSTOM_DATA1)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def build_terrain_master(name="M_SR_TerrainBlend"):
    """Vertex-colour layer blend for the Nanite terrain tiles exported by blender/lib/terrain.py.
    Vertex colour = sequential lerp factors: R blends L0->L1, G blends ->L2, B blends ->L3.
    Terrain UVs are in metres, so each layer has its own UVScale (= 1 / metres per repeat)."""
    folder = f"{DEST}/Materials"
    m, created = new_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return m
    X = mel.create_material_expression
    S = unreal.MaterialSamplerType
    P = unreal.MaterialProperty
    white, flat, mask = tex_asset("T_Default_D"), tex_asset("T_Default_N"), tex_asset("T_Default_R")
    uv = X(m, unreal.MaterialExpressionTextureCoordinate, -2200, 0)
    vc = X(m, unreal.MaterialExpressionVertexColor, -600, -900)
    # cliff layer (L1) is projected from the side (biplanar X/Z + Y/Z) so rock strata follow world height
    wp = X(m, unreal.MaterialExpressionWorldPosition, -2600, 300)
    to_m = X(m, unreal.MaterialExpressionMultiply, -2450, 300)
    cm = X(m, unreal.MaterialExpressionConstant, -2600, 420)
    cm.set_editor_property("r", 0.01)
    mel.connect_material_expressions(wp, "", to_m, "A")
    mel.connect_material_expressions(cm, "", to_m, "B")
    planes = []
    for comps in (("r", "b"), ("g", "b")):
        mk = X(m, unreal.MaterialExpressionComponentMask, -2300, 300 + len(planes) * 120)
        for c in "rgba":
            mk.set_editor_property(c, c in comps)
        mel.connect_material_expressions(to_m, "", mk, "Input")
        planes.append(mk)
    nws = X(m, unreal.MaterialExpressionVertexNormalWS, -2600, 600)
    absn = []
    for c in ("r", "g"):
        mk = X(m, unreal.MaterialExpressionComponentMask, -2450, 600 + len(absn) * 100)
        for cc in "rgba":
            mk.set_editor_property(cc, cc == c)
        mel.connect_material_expressions(nws, "", mk, "Input")
        ab = X(m, unreal.MaterialExpressionAbs, -2300, 600 + len(absn) * 100)
        mel.connect_material_expressions(mk, "", ab, "Input")
        absn.append(ab)
    ssum = X(m, unreal.MaterialExpressionAdd, -2150, 650)
    mel.connect_material_expressions(absn[0], "", ssum, "A")
    mel.connect_material_expressions(absn[1], "", ssum, "B")
    eps = X(m, unreal.MaterialExpressionAdd, -2050, 650)
    mel.connect_material_expressions(ssum, "", eps, "A")
    ce = X(m, unreal.MaterialExpressionConstant, -2150, 750)
    ce.set_editor_property("r", 0.001)
    mel.connect_material_expressions(ce, "", eps, "B")
    w_xz = X(m, unreal.MaterialExpressionDivide, -1950, 650)          # |ny| / (|nx| + |ny|)
    mel.connect_material_expressions(absn[1], "", w_xz, "A")
    mel.connect_material_expressions(eps, "", w_xz, "B")
    layers = []
    for k in range(4):
        y = -700 + k * 520
        sc = X(m, unreal.MaterialExpressionScalarParameter, -2000, y)
        sc.set_editor_property("parameter_name", f"L{k}_UVScale")
        sc.set_editor_property("default_value", 0.2)
        coords = []
        for src in ([uv] if k != 1 else planes):
            uvm = X(m, unreal.MaterialExpressionMultiply, -1800, y + 60 * len(coords))
            mel.connect_material_expressions(src, "", uvm, "A")
            mel.connect_material_expressions(sc, "", uvm, "B")
            coords.append(uvm)
        outs = {}
        for j, (pname, tex, smp) in enumerate((("Base", white, S.SAMPLERTYPE_COLOR), ("Normal", flat, S.SAMPLERTYPE_NORMAL),
                                               ("Rough", mask, S.SAMPLERTYPE_MASKS))):
            samples = []
            for ci, uvm in enumerate(coords):
                t = X(m, unreal.MaterialExpressionTextureSampleParameter2D, -1500 - ci * 250, y + j * 160)
                t.set_editor_property("parameter_name", f"L{k}_{pname}")
                if tex:
                    t.set_editor_property("texture", tex)
                t.set_editor_property("sampler_type", smp)
                try:
                    t.set_editor_property("sampler_source", unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
                except Exception:
                    pass
                mel.connect_material_expressions(uvm, "", t, "UVs")
                samples.append(t)
            if len(samples) == 1:
                outs[pname] = (samples[0], "RGB" if pname != "Rough" else "R")
            else:                               # blend the two side projections by the surface normal
                lp = X(m, unreal.MaterialExpressionLinearInterpolate, -1300, y + j * 160)
                ch = "RGB" if pname != "Rough" else "R"
                mel.connect_material_expressions(samples[1], ch, lp, "A")
                mel.connect_material_expressions(samples[0], ch, lp, "B")
                mel.connect_material_expressions(w_xz, "", lp, "Alpha")
                outs[pname] = (lp, "")
        tint = X(m, unreal.MaterialExpressionVectorParameter, -1250, y)
        tint.set_editor_property("parameter_name", f"L{k}_Tint")
        tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
        col = X(m, unreal.MaterialExpressionMultiply, -1050, y)
        mel.connect_material_expressions(outs["Base"][0], outs["Base"][1], col, "A")
        mel.connect_material_expressions(tint, "", col, "B")
        layers.append(dict(col=(col, ""), nrm=outs["Normal"], rgh=outs["Rough"]))

    def chain(key, x):
        cur = layers[0][key]
        for k, ch in ((1, "R"), (2, "G"), (3, "B")):
            lp = X(m, unreal.MaterialExpressionLinearInterpolate, x + k * 160, -500 + k * 120)
            mel.connect_material_expressions(cur[0], cur[1], lp, "A")
            mel.connect_material_expressions(layers[k][key][0], layers[k][key][1], lp, "B")
            mel.connect_material_expressions(vc, ch, lp, "Alpha")
            cur = (lp, "")
        return cur
    base = chain("col", -800)
    nrm = chain("nrm", -800)
    rgh = chain("rgh", -800)
    mel.connect_material_property(base[0], base[1], P.MP_BASE_COLOR)
    mel.connect_material_property(nrm[0], nrm[1], P.MP_NORMAL)
    rs = X(m, unreal.MaterialExpressionScalarParameter, -300, 400)
    rs.set_editor_property("parameter_name", "Roughness")
    rs.set_editor_property("default_value", 1.0)
    rm = X(m, unreal.MaterialExpressionMultiply, -150, 350)
    mel.connect_material_expressions(rgh[0], rgh[1], rm, "A")
    mel.connect_material_expressions(rs, "", rm, "B")
    mel.connect_material_property(rm, "", P.MP_ROUGHNESS)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def build_water_master(name="M_SR_Water"):
    """Opaque glossy sea: colour + two wave normal maps panning in different directions."""
    folder = f"{DEST}/Materials"
    m, created = new_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return m
    X = mel.create_material_expression
    P = unreal.MaterialProperty
    waves = tex_asset("T_WaterWaves_N") or tex_asset("T_Default_N")
    uv = X(m, unreal.MaterialExpressionTextureCoordinate, -1400, 0)
    samples = []
    for k, (sx, sy, scale) in enumerate(((0.012, 0.004, 1.0), (-0.006, 0.01, 0.43))):
        mul = X(m, unreal.MaterialExpressionMultiply, -1250, k * 300)
        sc = X(m, unreal.MaterialExpressionConstant, -1400, 150 + k * 300)
        sc.set_editor_property("r", scale)
        mel.connect_material_expressions(uv, "", mul, "A")
        mel.connect_material_expressions(sc, "", mul, "B")
        pan = X(m, unreal.MaterialExpressionPanner, -1050, k * 300)
        pan.set_editor_property("speed_x", sx)
        pan.set_editor_property("speed_y", sy)
        mel.connect_material_expressions(mul, "", pan, "Coordinate")
        t = X(m, unreal.MaterialExpressionTextureSampleParameter2D, -800, k * 300)
        t.set_editor_property("parameter_name", f"Waves{k}")
        if waves:
            t.set_editor_property("texture", waves)
        t.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        mel.connect_material_expressions(pan, "", t, "UVs")
        samples.append(t)
    blend = X(m, unreal.MaterialExpressionBlendAngleCorrectedNormals, -500, 150)
    mel.connect_material_expressions(samples[0], "RGB", blend, "BaseNormal")
    mel.connect_material_expressions(samples[1], "RGB", blend, "AdditionalNormal")
    mel.connect_material_property(blend, "", P.MP_NORMAL)
    col = X(m, unreal.MaterialExpressionVectorParameter, -500, -250)
    col.set_editor_property("parameter_name", "Tint")
    col.set_editor_property("default_value", unreal.LinearColor(0.02, 0.12, 0.16, 1))
    mel.connect_material_property(col, "", P.MP_BASE_COLOR)
    for pname, val, prop, y in (("Roughness", 0.04, P.MP_ROUGHNESS, 450), ("Specular", 0.6, P.MP_SPECULAR, 550)):
        e = X(m, unreal.MaterialExpressionScalarParameter, -500, y)
        e.set_editor_property("parameter_name", pname)
        e.set_editor_property("default_value", val)
        mel.connect_material_property(e, "", prop)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def setup_terrain_instance(mi, e):
    LC = unreal.LinearColor
    tints = e.get("tints") or [[1, 1, 1]] * 4
    for k, (layer, tile) in enumerate(zip(e.get("layers", []), e.get("tiles", []))):
        for suf, pname in (("D", "Base"), ("N", "Normal"), ("R", "Rough")):
            t = tex_asset(f"T_{layer}_{suf}")
            if t:
                mel.set_material_instance_texture_parameter_value(mi, f"L{k}_{pname}", t)
        mel.set_material_instance_scalar_parameter_value(mi, f"L{k}_UVScale", 1.0 / float(tile))
        c = tints[k] if k < len(tints) else [1, 1, 1]
        mel.set_material_instance_vector_parameter_value(mi, f"L{k}_Tint", LC(c[0], c[1], c[2], 1))


def parent_for(entry, masters):
    kind = entry.get("kind", "opaque")
    if kind == "terrain":
        return masters["terrain"]
    if kind == "water":
        return masters["water"]
    if kind == "carpaint":
        return masters["carpaint"]
    if kind == "glass":
        return masters["glass"]
    if kind == "foliage":
        return masters["foliage"]
    if kind == "emissive" and entry.get("alpha", 1.0) < 1.0:
        return masters["vfx"]
    return masters["master"]


def build_instances():
    with open(os.path.join(ASSETS, "materials.json")) as f:
        manifest = json.load(f)
    masters = dict(master=build_master("M_SR_Master"), carpaint=build_master("M_SR_CarPaint", clear_coat=True),
                   glass=build_master("M_SR_Glass", translucent=True), foliage=build_master("M_SR_Foliage", two_sided=True),
                   vfx=build_master("M_SR_VFX", vfx=True), terrain=build_terrain_master(),
                   water=build_water_master())
    folder = f"{DEST}/Materials/Instances"
    out = {}
    for name, e in manifest.items():
        mi_name = "MI_" + (name[2:] if name.startswith("M_") else name)
        mi, _ = new_asset(mi_name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        parent = parent_for(e, masters)
        mel.set_material_instance_parent(mi, parent)
        LC = unreal.LinearColor
        col = e.get("color") or [1, 1, 1]
        if parent == masters["terrain"]:
            setup_terrain_instance(mi, e)
        elif parent == masters["water"]:
            col = e.get("color") or [0.02, 0.12, 0.16]
            mel.set_material_instance_vector_parameter_value(mi, "Tint", LC(col[0], col[1], col[2], 1))
            mel.set_material_instance_scalar_parameter_value(mi, "Roughness", float(e.get("rough", 0.04)))
        elif parent == masters["vfx"]:
            em = e.get("emit") or col
            mel.set_material_instance_vector_parameter_value(mi, "EmissiveColor", LC(em[0], em[1], em[2], 1))
            mel.set_material_instance_scalar_parameter_value(mi, "EmissiveStrength", float(e.get("emit_str") or 5.0))
            mel.set_material_instance_scalar_parameter_value(mi, "Opacity", float(e.get("alpha", 0.6)))
        else:
            mel.set_material_instance_vector_parameter_value(mi, "Tint", LC(col[0], col[1], col[2], 1))
            mel.set_material_instance_scalar_parameter_value(mi, "Metallic", float(e.get("metal", 0.0)))
            tex = e.get("tex")
            img = e.get("image")
            has_r = False
            if tex:
                for suf, pname in (("D", "BaseTex"), ("N", "NormalTex"), ("R", "RoughTex"), ("E", "EmissiveTex")):
                    t = tex_asset(f"T_{tex}_{suf}")
                    if t:
                        mel.set_material_instance_texture_parameter_value(mi, pname, t)
                        has_r = has_r or suf == "R"
            if img:
                t = tex_asset(os.path.splitext(os.path.basename(img))[0])
                if t:
                    mel.set_material_instance_texture_parameter_value(mi, "BaseTex", t)
                    if e.get("image_emit"):
                        mel.set_material_instance_texture_parameter_value(mi, "EmissiveTex", t)
            mel.set_material_instance_scalar_parameter_value(mi, "Roughness", 1.0 if has_r else float(e.get("rough", 0.5)))
            strength = float(e.get("emit_str") or 0.0)
            if e.get("emit") or (tex and tex_asset(f"T_{tex}_E")) or e.get("image_emit"):
                em = e.get("emit") or [1, 1, 1]
                mel.set_material_instance_vector_parameter_value(mi, "EmissiveColor", LC(em[0], em[1], em[2], 1))
                mel.set_material_instance_scalar_parameter_value(mi, "EmissiveStrength", strength or 2.0)
            if parent == masters["glass"]:
                op = max(0.15, 1.0 - 0.8 * float(e.get("transmission", 0.7)))
                mel.set_material_instance_scalar_parameter_value(mi, "Opacity", op)
        eal.save_loaded_asset(mi)
        out[name] = mi
    log(f"material instances: {len(out)}")
    return out, manifest


# ------------------------------------------------------------------- meshes ---
def fbx_options(skeletal):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    if skeletal:
        ui.set_editor_property("import_as_skeletal", True)
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        ui.set_editor_property("create_physics_asset", True)
        sk = ui.get_editor_property("skeletal_mesh_import_data")
        sk.set_editor_property("import_morph_targets", False)
    else:
        ui.set_editor_property("import_as_skeletal", False)
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        sm = ui.get_editor_property("static_mesh_import_data")
        sm.set_editor_property("combine_meshes", True)
        sm.set_editor_property("auto_generate_collision", True)
        for prop, val in (("generate_lightmap_u_vs", False), ("build_nanite", USE_NANITE)):
            try:
                sm.set_editor_property(prop, val)
            except Exception:
                pass
    return ui


def import_fbx(path, dest, skeletal=False):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path)
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", fbx_options(skeletal))
    tools.import_asset_tasks([t])
    return [eal.load_asset(p) for p in t.get_editor_property("imported_object_paths")]


TRANSLUCENT_KINDS = ("glass",)


def assign_materials(asset, instances, manifest):
    """Match FBX slot names (= Blender material names) to MI_ instances."""
    translucent = False
    if isinstance(asset, unreal.StaticMesh):
        slots = asset.get_editor_property("static_materials")
        for i, s in enumerate(slots):
            nm = str(s.get_editor_property("imported_material_slot_name") or s.get_editor_property("material_slot_name"))
            mi = instances.get(nm)
            if mi:
                asset.set_material(i, mi)
                e = manifest.get(nm, {})
                translucent |= e.get("kind") in TRANSLUCENT_KINDS or (e.get("kind") == "emissive" and e.get("alpha", 1) < 1)
        if translucent and USE_NANITE:      # Nanite cannot render translucent sections
            ns = asset.get_editor_property("nanite_settings")
            ns.set_editor_property("enabled", False)
            asset.set_editor_property("nanite_settings", ns)
    elif isinstance(asset, unreal.SkeletalMesh):
        mats = asset.get_editor_property("materials")
        for s in mats:
            nm = str(s.get_editor_property("imported_material_slot_name") or s.get_editor_property("material_slot_name"))
            mi = instances.get(nm)
            if mi:
                s.set_editor_property("material_interface", mi)
        asset.set_editor_property("materials", mats)
    eal.save_loaded_asset(asset)


def complex_collision(asset):
    """Landmarks / roads / rocks: use the render mesh for collision so cars can drive through arches."""
    try:
        bs = asset.get_editor_property("body_setup")
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(asset)
    except Exception as ex:  # noqa: BLE001
        log(f"collision setup skipped for {asset.get_name()}: {ex}")


SIMPLE_COLLISION_PREFIXES = ("SM_Barrier", "SM_Cone", "SM_TireStack", "SM_Card", "SM_VFX", "SM_Falcon", "SM_Drone",
                             "SM_Lantern", "SM_StringLights", "SM_Flag", "SM_HotAirBalloon", "SM_Boost",
                             # life kit: people, animals, traffic and trackside props use cheap convex collision
                             "SM_Person", "SM_Crowd", "SM_Camel", "SM_Goat", "SM_Sheep", "SM_Car_", "SM_Bus", "SM_Truck",
                             "SM_Chevron", "SM_Sponsor", "SM_Distance", "SM_Bench", "SM_Lamp", "SM_Kiosk", "SM_Gazebo",
                             "SM_BeachUmbrella", "SM_Shrub", "SM_StackedTyres", "SM_RockGrey", "SM_FoodTruck",
                             "SM_MarshalPost", "SM_Campfire", "SM_Bird", "SM_Seagulls", "SM_Helicopter", "SM_Bunting",
                             "SM_Grass", "SM_Flowers")
NO_COLLISION_PREFIXES = ("SM_VFX", "SM_Lantern", "SM_StringLights", "SM_Flag", "SM_SouqAwning", "SM_HotAirBalloon",
                         "SM_Drone", "SM_CardPickup", "SM_Card", "SM_BirdFlock", "SM_Seagulls", "SM_Helicopter",
                         "SM_Bunting", "SM_GrassTuft", "SM_Flowers")


def import_kits(instances, manifest):
    for kit in KITS:
        src = os.path.join(ASSETS, kit)
        if not os.path.isdir(src):
            continue
        dest = f"{DEST}/{kit.capitalize()}"
        files = sorted(f for f in os.listdir(src) if f.lower().endswith(".fbx"))
        with unreal.ScopedSlowTask(len(files), f"Sahara Racers: importing {kit}") as task:
            task.make_dialog(True)
            for f in files:
                if task.should_cancel():
                    return
                task.enter_progress_frame(1, f)
                for a in import_fbx(os.path.join(src, f), dest):
                    if not a:
                        continue
                    assign_materials(a, instances, manifest)
                    name = a.get_name()
                    if isinstance(a, unreal.StaticMesh) and not name.startswith(SIMPLE_COLLISION_PREFIXES):
                        complex_collision(a)
        log(f"kit {kit}: {len(files)} meshes")


def import_cars(instances, manifest):
    root = os.path.join(ASSETS, "cars")
    for car in sorted(os.listdir(root)):
        folder = os.path.join(root, car)
        if not os.path.isdir(folder) or car == "textures":
            continue
        dest = f"{DEST}/Cars/{car}"
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith(".fbx"):
                continue
            for a in import_fbx(os.path.join(folder, f), dest, skeletal=f.startswith("SK_")):
                if a and isinstance(a, (unreal.StaticMesh, unreal.SkeletalMesh)):
                    assign_materials(a, instances, manifest)
        log(f"car {car} imported -> {dest}")


def main():
    force_legacy_fbx()
    import_textures()
    instances, manifest = build_instances()
    import_kits(instances, manifest)
    if IMPORT_CARS:
        import_cars(instances, manifest)
    log("done. Next: unreal/build_map.py assembles the race maps; docs/MAPS.md and docs/UNREAL_SETUP.md explain the rest.")


if __name__ == "__main__":      # build_map.py loads this file as a module to reuse the helpers
    main()
