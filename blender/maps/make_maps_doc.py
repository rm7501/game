"""Write docs/MAPS.md from the built map folders (track.json numbers + the design notes below).

Run after building the maps:  python blender/maps/make_maps_doc.py
Also converts docs/previews/maps/*.png renders to compact .jpg files.
"""
import glob
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

MAPS = [
    dict(name="RiyadhNights", title="Riyadh Nights — ليالي الرياض", sub="Olaya Interchange to Wadi Hanifa", key="riyadh",
         concept="Golden hour turning to night over a flat desert city of highways, flyovers with loop ramps and the "
                 "elevated Metro, with KAFD and Kingdom Centre rising out of it. The lap then drops off the Tuwaiq "
                 "limestone escarpment into the green Wadi Hanifa and climbs back through the mud-brick ruins of "
                 "Diriyah (At-Turaif).",
         lap=["Start on **King Fahd Road** (palms, gantry signs, a canyon of towers, Kingdom Centre on the right)",
              "Up the **flyover** and round a descending **270° loop ramp** that passes *under* the flyover",
              "**KAFD chicane** between the towers",
              "**Escarpment cliff road** with a hairpin, down the stepped limestone ledges",
              "**Wadi Hanifa** floor: palm groves, the lake, a wide meander",
              "Climb out to **Diriyah**: cobbled S-bends between mud-brick walls, Masmak-style fort",
              "Sweeping last corner past the stadium back onto King Fahd Road"],
         hints={"Shortcut_StadiumCut": "Inside the last corner: cut straight across the stadium car park instead of following the sweep.",
                "Shortcut_MetroLeap": "In the KAFD chicane, cones and a water barrier hide a construction ramp onto the unfinished "
                                      "Metro viaduct. Ride it to where it stops at the cliff edge and fly down onto the hairpin road.",
                "Shortcut_PalmTrail": "On the wadi floor, a dirt trail slips into the palm grove and runs straight while the road "
                                      "follows the meander.",
                "Shortcut_DiriyahBreach": "At the first ruins bend, a breach in the old mud wall leads down a narrow cobbled lane "
                                          "that skips the S-bends."}),
    dict(name="AlUla", title="AlUla — العُلا", sub="Hegra Canyon Rally", key="alula",
         concept="A golden sand valley winding between towering, honeycomb-eroded sandstone massifs. The landmarks sit in "
                 "the landscape: Maraya reflecting the canyon, Qasr al-Farid alone on the plain, Hegra tombs carved into "
                 "a cliff, a land-art sand labyrinth with a palm at its centre, and Elephant Rock lit by lanterns at dusk.",
         lap=["Start at the **Maraya** mirror building, packed-sand rally road with berms",
              "Across the open plain past **Qasr al-Farid**",
              "Under the **Rainbow Rock** arch into the **Grand Canyon S-bends** between cliffs",
              "Round the **sand labyrinth**",
              "Along the **Hegra tomb cliff**",
              "Round the **giant dune**",
              "Through the **Elephant Rock lantern lounge**, then the southern plain back to Maraya"],
         hints={"Shortcut_ElephantArch": "At Elephant Rock, aim straight through the gap under the trunk instead of going round the rock.",
                "Shortcut_SlotCanyon": "Before the canyon S-bends, a boulder pile hides a 7 m crack that runs straight through the "
                                       "whole north massif.",
                "Shortcut_LabyrinthRun": "Straight across the sand spiral. Its ridges make it bumpy.",
                "Shortcut_DuneJump": "Over the crest of the giant dune instead of round it. Land straight."}),
    dict(name="JeddahCorniche", title="Jeddah — جدة", sub="Corniche & Al-Balad", key="jeddah",
         concept="Jeddah from the sea in: the Corniche with the floating mosque, the curved seawall, palms and white "
                 "railings, then the old town of Al-Balad with string lights over narrow lanes and teal/brown "
                 "rawasheen houses. A lagoon cuts in from the Red Sea.",
         lap=["Start on the **Corniche**, sea and breakwater on the left",
              "Swing inland round the **palm park**, then past the **floating mosque**",
              "Over the **cove bridge** and round to the north",
              "Through the great **Bab Makkah** gate into **Al-Balad**: cobbled lanes, rawasheen, string lights and awnings",
              "**Nassif House** plaza",
              "Round the east end of the **lagoon** and over the **lagoon-mouth bridge** back to the Corniche"],
         hints={"Shortcut_BeachRun": "Where the Corniche swings inland round the park, drop onto the sand and race along the waterline.",
                "Shortcut_SouqPassage": "In Al-Balad, a souq stall hides the mouth of a covered souq alley that runs straight through a block.",
                "Shortcut_LagoonJump": "Before the lagoon, take the old fishing pier and launch off its end across the lagoon mouth."}),
    dict(name="AsirMountains", title="Asir — عسير", sub="Soudah Switchbacks", key="asir",
         concept="The green Asir escarpment: a serpentine of hairpins stacked up a mountain nose, a road along a "
                 "knife-edge ridge with drops on both sides, morning mist lying in the valleys, juniper forest, "
                 "terraced fields and the stone tower houses of Rijal Almaa, linked to the top by the Soudah cable car.",
         lap=["Start on the **Rijal Almaa** village plaza (stone walls, tower houses climbing the hill)",
              "**Valley road** along the wadi, bowing round a terraced knoll",
              "**Three stacked hairpins** up the mountain nose (guardrail on the drop side, cut rock on the other)",
              "The **knife-edge ridge road**, with Asiri watchtowers, mist below and drops both sides",
              "Straight through the **Soudah peak tunnel**",
              "Long **sweeping descent** through the juniper forest, across a **stone viaduct**, past terraces",
              "Back into the village"],
         hints={"Shortcut_WadiRun": "At the start of the valley road, drop into the dry riverbed and blast along the gravel.",
                "Shortcut_SaddleJump": "Before the tunnel, the old road climbs over the peak's shoulder and ends at a washed-out "
                                       "bridge. Jump the ravine and land on the descent.",
                "Shortcut_GoatTrack": "At the top of the descent, two big junipers hide a rutted goat track that plunges straight "
                                      "down through the forest.",
                "Shortcut_MulePath": "Near the end, a gap between two dry-stone walls opens onto a stepped mule path down the "
                                     "terraces past the village."}),
    dict(name="FutureCity", title="Future City — NEOM", sub="The Line Circuit", key="future",
         concept="No reference photos for this one, so it follows the NEOM idea: The Line, a 500 m tall mirrored "
                 "megastructure running dead straight through desert and mountains with a green, terraced canyon inside; "
                 "Oxagon, an octagonal port city floating on the Red Sea; maglev lines, solar trees and wind helixes. "
                 "Blue hour, everything glowing.",
         lap=["Start **inside The Line**: glow road, terraces and sky bridges overhead",
              "Canyon **chicanes** under the Skyway",
              "Out through a **portal** in The Line's south wall",
              "A big **banked curve** (15°) wrapped round a granite mountain",
              "**Futuristic bridge** over a fjord-like gorge",
              "Bridge out to **Oxagon** and once round the octagon",
              "North up the **mountain valley** S-bends beside the maglev",
              "Back in through a second portal"],
         hints={"Shortcut_Skyway": "Right after the start, ramp up onto the elevated deck down the middle of the canyon, above the chicanes.",
                "Shortcut_MarinaJump": "On Oxagon, go straight on instead of turning, and launch over the marina basin through the city's core.",
                "Shortcut_MaglevLine": "In the valley, solar trees hide a service ramp up onto the maglev guideway. "
                                       "It runs dead straight while the road snakes."}),
]


def side_of(track, sc):
    """'left' / 'right': which side of the main road a shortcut leaves on."""
    main = track["main"]
    s0 = sc["joins_main_at_m"][0]
    m = min(main, key=lambda p: abs(p["s"] - s0))
    q = next((p for p in sc["samples"] if p["s"] >= 35), sc["samples"][-1])
    yaw = math.radians(m["yaw"])                    # UE yaw (clockwise, +Y right)
    fx, fy = math.cos(yaw), math.sin(yaw)
    dx, dy = q["x"] - m["x"], q["y"] - m["y"]
    cross = fx * dy - fy * dx                       # UE: +Y is to the right of +X
    return "right" if cross > 0 else "left"


def jpg_previews():
    from PIL import Image
    folder = os.path.join(ROOT, "docs", "previews", "maps")
    for p in sorted(glob.glob(os.path.join(folder, "*.png"))):
        Image.open(p).convert("RGB").save(p[:-4] + ".jpg", quality=88, optimize=True)
        os.remove(p)


def main():
    jpg_previews()
    out = ["# The five race maps", "",
           "Every map is a full **2 × 2 km** race environment built in Blender. Each one has:",
           "",
           "* a sculpted terrain",
           "* a closed race lap with bridges, tunnels, kerbs and barriers",
           "* **3–4 shortcuts (most of them hidden)**",
           "* the kit landmarks placed in the landscape",
           "* gameplay data: checkpoints, start grid, card pickups, boost pads and an AI racing line",
           "",
           "**No empty edges.** A backdrop continues every landscape from the map edge to the horizon (about 24 km). "
           "Riyadh's lit city sprawls on with its tower corridor, AlUla's massifs roll on, the Red Sea and the Hijaz "
           "mountains frame Jeddah, the Sarawat ranges surround Asir, and The Line runs off to both horizons.",
           "",
           "**Alive.** Every map has a race-day crowd. Spectators stand behind fences with flags, and the fan zones have "
           "gazebos, food trucks and car parks. There are camera towers, marshal posts, sponsor boards and a TV "
           "helicopter. Every tight corner has red-and-white chevrons, with tyre walls and braking boards.",
           "",
           "On top of that, each map has local life:",
           "",
           "* **Riyadh:** traffic and mosques, plus picnics in the wadi.",
           "* **AlUla:** Bedouin camps and camel caravans.",
           "* **Jeddah:** dhows, fishing boats and families on the beach.",
           "* **Asir:** goat herds and shepherds, plus viewpoints.",
           "* **Future City:** people in The Line's park, yachts and air taxis.",
           "",
           "The maps use the concept of each place from the reference photos. They are not replicas.", "",
           "| Map | Lap | Climb | Shortcuts |", "|---|---|---|---|"]
    rows, body = [], []
    for M in MAPS:
        folder = os.path.join(ROOT, "assets", "maps", M["name"])
        with open(os.path.join(folder, "track.json")) as f:
            tr = json.load(f)
        zs = [p["z"] / 100 for p in tr["main"]]
        hidden = sum(1 for s in tr["shortcuts"] if s["hidden"])
        rows.append(f"| [{M['title']}](#{M['key']}) | {tr['length_m'] / 1000:.2f} km | {max(zs) - min(zs):.0f} m | "
                    f"{len(tr['shortcuts'])} ({hidden} hidden) |")
        imgs = sorted(glob.glob(os.path.join(ROOT, "docs", "previews", "maps", f"{M['name']}_*.jpg")))
        rel = [os.path.relpath(p, os.path.join(ROOT, "docs")).replace(os.sep, "/") for p in imgs]
        b = [f'<a id="{M["key"]}"></a>', "", f"## {M['title']} — *{M['sub']}*", ""]
        if rel:
            b += [f"![{M['name']}]({rel[0]})", ""]
        b += [f"**Concept.** {M['concept']}", "", f"**The lap ({tr['length_m'] / 1000:.2f} km, "
              f"{len(tr['checkpoints'])} checkpoints):**", ""]
        b += [f"{k + 1}. {s}" for k, s in enumerate(M["lap"])]
        b += ["", "| Shortcut | Type | Length | Saves | Leaves the road at | How to find it |", "|---|---|---|---|---|---|"]
        for sc in tr["shortcuts"]:
            kind = "hidden" if sc["hidden"] else "visible"
            b.append(f"| **{sc['label']}** | {kind} | {sc['length_m']:.0f} m | {sc['saves_m']:.0f} m | "
                     f"{sc['joins_main_at_m'][0]:.0f} m into the lap, {side_of(tr, sc)} | {M['hints'].get(sc['name'], '')} |")
        b += ["", "| Minimap | More views |", "|---|---|"]
        more = " ".join(f"![]({p})" for p in rel[1:4])
        b += [f"| ![minimap](../assets/maps/{M['name']}/minimap.png) | {more} |", ""]
        if len(rel) > 4:
            b += [" ".join(f"![]({p})" for p in rel[4:]), ""]
        b += ["---", ""]
        body += b
    out += rows + ["", "*(Renders: Blender Cycles previews of the exported maps; the cars are the game cars.)*", "", "---", ""]
    out += body
    out += [
        "## Building a map in Unreal", "",
        "1. Run `unreal/import_assets.py` once (textures, materials, kits, cars).",
        "2. **File → New Level → Empty Level**, save it (e.g. `/Game/SaharaRacers/Maps/L_AsirMountains`).",
        "3. Output Log (Python): `exec(open(r\"C:/path/to/game/unreal/build_map.py\").read())`, then `build(\"AsirMountains\")`.",
        "",
        "`build()` imports `assets/maps/<Map>/` and builds everything in the level:",
        "* terrain tiles, road chunks and water",
        "* every prop in `layout.json`",
        "* the start grid, checkpoint triggers, card pickups, boost pads and waypoints for the racing line and the shortcuts",
        "* the lighting preset",
        "",
        "All actors are tagged (`SR_Checkpoint`, `SR_CP_<n>`, `SR_Grid_<n>`, `SR_CardPickup`, `SR_BoostPad`, `SR_Line_<n>`, "
        "`SR_Shortcut`, `SR_Hidden`, …), so your Blueprints can find them with *Get All Actors With Tag*. To spawn your own "
        "pickup or checkpoint Blueprints instead of the marker meshes, set `ITEM_CLASSES` at the top of the script.",
        "",
        "**Landscape instead of mesh terrain.** `build(\"AlUla\", terrain=\"none\")`, then *Landscape mode → New → Import from File* "
        "with `assets/maps/<Map>/landscape/H_<Map>.png`. Use the location and scale from `landscape.json`; `landscape_help(\"AlUla\")` "
        "prints them. Weightmaps for the 4 paint layers are next to it.", "",
        "## Files per map (`assets/maps/<Map>/`)", "",
        "| File | What |", "|---|---|",
        "| `SM_<Map>_Terrain_<r>_<c>.fbx` | 4×4 Nanite terrain tiles; vertex colour = layer blend (M_SR_TerrainBlend) |",
        "| `SM_<Map>_Track_NN.fbx`, `SM_<Map>_Shortcut_*.fbx` | road chunks: surface, shoulders, kerbs, barriers, bridges, tunnels |",
        "| `SM_<Map>_Water.fbx` | sea / lake plane (if the map has water) |",
        "| `props/` | map-specific landmarks (The Line portal, Oxagon, floating mosque, sand labyrinth, cable car, …) |",
        "| `layout.json` | every placed prop: kit, asset, Unreal location (cm), yaw, scale |",
        "| `track.json` | racing line (every 5 m: position, yaw, width, bank, air/tunnel/bridge), shortcuts with their savings, "
        "checkpoints, 8-car grid, pickups and boosts, all in Unreal units |",
        "| `landscape/` | 2017×2017 16-bit heightmap, 4 weightmaps, `landscape.json` |",
        "| `minimap.png` | top-down map (white = lap, orange = shortcut, magenta = hidden shortcut) |", "",
        "## Changing a map", "",
        "Each map is one Python file in `blender/maps/` (`riyadh.py`, `alula.py`, `jeddah.py`, `asir.py`, `future.py`):",
        "",
        "* `make_terrain()` sculpts the heightfield.",
        "* `tracks()` lists the control points of the lap and the shortcuts: width, height, banking, barrier style, "
        "surface, and tags (tunnel, gap = jump, bridge).",
        "* `dress()` places the props.",
        "",
        "Rebuild with:", "",
        "```", "python blender/maps/asir.py --layout     # quick: just the minimap -> /tmp/claude-0/asir_layout.png",
        "python blender/maps/asir.py              # full build + exports + preview renders (SR_PREVIEW=1 for fast renders)",
        "python blender/maps/make_maps_doc.py     # refresh this page", "```", "",
        "The shared engine is in `blender/lib/`:",
        "",
        "* `terrain.py`: heightfield, noise, carving, Landscape and mesh export.",
        "* `track.py`: splines, road, bridge and tunnel meshes, gameplay JSON, minimap.",
        "* `mapkit.py`: prop placement, export and previews.", ""]
    with open(os.path.join(ROOT, "docs", "MAPS.md"), "w") as f:
        f.write("\n".join(out))
    print("wrote docs/MAPS.md")


if __name__ == "__main__":
    main()
