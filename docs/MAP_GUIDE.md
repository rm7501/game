# Map guide — making each track instantly recognisable

> **The finished race maps are in [MAPS.md](MAPS.md):** terrain, laps, shortcuts and a one-call Unreal build.
> This guide covers the kits: what makes each place recognisable. Use it to dress extra tracks or tweak the maps.

The single biggest reason a map "doesn't look like Riyadh" or "doesn't look like AlUla" is missing
**landmarks on the skyline** and missing **local architecture along the track**. Each kit gives you
both. Below: what defines each place, which assets to use, a suggested layout and the light.

All sizes are real-world; don't scale the landmarks down. Place them far away instead, as players
judge size from the road.

---

## 1. Riyadh Nights — ليالي الرياض

![Riyadh Nights](previews/map_riyadh_nights.png)

**What makes it Riyadh**
* **Kingdom Centre** (برج المملكة, 302 m), with its lit parabolic opening and the sky bridge at the top. Every
  Riyadh skyline shot has it. Turn its *broad face* (the side with the opening) towards the track.
* **Al Faisaliah** (برج الفيصلية, 267 m), a pencil-shaped tower with a **golden globe** and green edge lights.
* **KAFD**: a cluster of modern towers, led by the crystalline **PIF Tower** (385 m) with diamond LED lines.
* **King Fahd Road**: a wide boulevard with palms in the median, tall double-arm lights and green
  Arabic/English gantry signs.
* **Najdi-modern buildings**: beige stone, narrow vertical windows and **triangular Najdi crenellations**
  on every parapet. This motif matters most of all. Plain glass boxes look like any city.
* The **Masmak** fortress for a historic section; the **TV Tower** on the horizon.

**Kit**: `assets/riyadh/` — KingdomCentre, KingdomMall, AlFaisaliah, RiyadhTVTower, PIFTower,
KAFD_Twist/Slant/Diagrid/Stepped, Masmak, RiyadhBlock_01–06, Road_KingFahd_25m, StreetLight_KFR,
Gantry_KFR, MetroViaduct_30m, MetroCar, Billboard_LED.

**Layout idea**: main straight down King Fahd Road towards Kingdom Centre (as in the preview). Turn
right through KAFD (tight corners between towers). Run back along the Metro viaduct and finish with a
night section past the floodlit Masmak walls. Line the road with RiyadhBlocks 40–60 m back, and put
KAFD towers 100–150 m back so the skyline stays visible.

**Light**: `setup("riyadh")`. Bloom on, dark purple sky, warm street-lamp pools (point lights under
`SM_StreetLight_KFR` heads, 2700–3500 K).

---

## 2. AlUla — العُلا

![AlUla](previews/map_alula.png)

**What makes it AlUla**
* **Hegra (مدائن صالح)**: Nabataean tombs carved into sandstone outcrops. `SM_QasrAlFarid` is the famous
  lone tomb, with four pilasters, a double cornice, an attic storey and **crow-step crenellations**.
* **Elephant Rock (جبل الفيل)**: 50 m tall, with the trunk forming a **drive-through arch**.
* **Maraya (مرايا)**: the mirror-clad concert hall. It reflects the canyon, so place it where it mirrors rocks
  and sky.
* Towering **fluted sandstone** cliffs and hoodoos in warm tan with dark desert-varnish streaks. The
  `T_SandstoneStrata` texture and rock shapes are built for this.
* Palm oases, acacias, the mud-brick **Old Town**, and hot-air balloons (the AlUla Skies festival).

**Kit**: `assets/alula/` — QasrAlFarid, HegraTombCliff, ElephantRock, RainbowRock, Maraya,
RockPillar_A/B, Mesa_A, Boulder_A–C, AlUlaHouse_A/B, AlUlaOldTown, HotAirBalloon_A–C, Dune_A,
Road_Desert_25m (+ palms and acacia from `common`).

**Layout idea**: a desert road through a canyon of Mesa walls with Hegra tombs on the outside of fast
bends. A shortcut leads **through** Elephant Rock's arch. Pass by Maraya so its reflection shows the
racers, then end with a sprint through the palm oasis to the Old Town.

**Light**: `setup("alula")`. Golden hour with long shadows, warm dust haze.

---

## 3. Jeddah Al-Balad — جدة التاريخية (البلد)

![Jeddah Al-Balad](previews/map_jeddah_albalad.png)

**What makes it Al-Balad**
* Tall **coral-stone houses** in white-cream with timber courses (*takaleel*) every ~1 m.
* **Rawasheen (رواشين)**: projecting wooden lattice bay windows stacked over several floors, painted
  teal, green, blue, brown or white. These are *the* signature. Every house in the kit has 1–4 stacks.
* Narrow souq lanes with **fabric awnings, lanterns and string lights**, carved wooden doors and
  *markaz* benches.
* **Bayt Nassif** with the famous tree in front, white minarets, and the old gates (**Bab Makkah**).

**Kit**: `assets/jeddah/` — HijaziHouse_01–06, NassifHouse, Roshan_2F/3F (to dress your own
buildings), HijaziMinaret, BabMakkah, SouqAwning, Lantern, StringLights, SouqStall, MarkazBench,
Lane_Paving_20m.

**Layout idea**: street racing through 10 m lanes (the `Lane_Paving` width fits two cars) with 90°
corners at house corners. Put a covered souq section with awnings and lanterns, a fast straight
through Bab Makkah, and a plaza around Nassif House. Vary rotation and order so the rawasheen colours
mix.

**Light**: `setup("jeddah")`. Sunset over the Red Sea, humid haze, lanterns glowing (add point
lights at `SM_Lantern`, 2200 K).

---

## 4. Asir Mountains — جبال عسير

![Asir](previews/map_asir_mountains.png)

**What makes it Asir**
* **Rijal Almaa (رجال ألمع)** stone tower-houses: dark stacked stone, **white-painted window surrounds**,
  colourful shutters, and white stepped crenellations.
* **Asiri mud towers (قصبة)** with protruding slate rain ledges every ~35 cm. The ribbed silhouette is
  unique to the region.
* **Al-Qatt Al-Asiri (القط العسيري)**: bold geometric paintings (UNESCO heritage), on `SM_QattDoor` and
  every house door.
* Green **terraced** slopes, juniper (عرعر) forests, mist in the valleys, a dramatic **escarpment**, and
  the **Abha cable car**.

**Kit**: `assets/asir/` — RijalAlmaaHouse_01–04, RijalAlmaaVillage, AsiriMudTower_A/B, QattDoor,
TerraceHill, AsirMountain_A/B, Juniper_A/B, CableCar_Pylon/Cabin, Road_Mountain_25m,
Guardrail_10m, TunnelPortal, RetainingWall_20m.

**Layout idea**: a winding mountain pass with hairpins, guardrails on the valley side and retaining
walls on the hill side. A tunnel leads into the valley with the Rijal Almaa village. Run along the
terraces under the cable car, and finish with a fog-covered descent.

**Light**: `setup("asir")`. Low morning sun, dense valley fog (volumetric), clouds.

---

## 5. Future City (NEOM) — مدينة المستقبل (نيوم)

![Future City](previews/map_future_city.png)

**What makes it NEOM**
* **The Line**: two 500 m tall mirror walls with a lush terraced canyon between them. The canyon is the
  race track. `SM_TheLine_Segment` is 200 m long and **tiles seamlessly**, so place copies every 200 m
  along X.
* Organic terraces with planting, sky bridges, a maglev overhead, drones, glowing lane lines and holo
  gates.

**Kit**: `assets/future/` — TheLine_Segment, NeomTower_Petal, NeomTower_Halo,
MaglevGuideway_30m, MaglevCar, HoloArch, FutureBarrier_10m, FutureStreetLight, Drone, SolarTree,
WindHelix, Road_Future_25m.

**Layout idea**: a long high-speed run inside The Line, then exit through a gap into the desert past
the Petal and Halo towers. Use the maglev guideway as an overhead landmark, and place `SM_HoloArch`
for checkpoints.

**Light**: `setup("future")`. Blue hour with strong bloom; the emissive strips do the rest.

---

## Shared gameplay pieces (`assets/common/`)

Palms (3 sizes), acacia, water/concrete barriers, tyre stacks, cones, **Checkpoint Arch** (Najdi
style, Arabic + English banner), **Start Gantry** (with start lights), boost pad, jump ramp, card
pickup + cards, ability VFX meshes, grandstand and pennants.
