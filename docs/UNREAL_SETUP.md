# Unreal Engine 5 setup — Sahara Racers asset pack

Everything in `assets/` is ready for UE 5.1+ (tested API surface: UE 5.3–5.6). Units are real-world
metres in Blender → centimetres in Unreal, forward axis is **+X**, up is **+Z**.

---

## 1. One-click import

1. Clone or download this repo anywhere on your PC (it does not need to be inside the Unreal project).
2. In your project: **Edit → Plugins → "Python Editor Script Plugin" → Enable**, restart the editor.
3. **Tools → Execute Python Script…** → pick `unreal/import_assets.py`.

The script creates `/Game/SaharaRacers/`:

| Folder | Contents |
|---|---|
| `Textures/` | all tileable PBR textures (+ per-kit signs, plates, card art). Normal maps are flipped to DirectX automatically. |
| `Materials/` | 5 master materials: `M_SR_Master`, `M_SR_CarPaint` (clear coat), `M_SR_Glass`, `M_SR_Foliage` (two-sided), `M_SR_VFX` (additive) |
| `Materials/Instances/` | one `MI_*` per material in `assets/materials.json` (car paints, facades, sandstone, coral stone…) |
| `Common/ Riyadh/ Alula/ Jeddah/ Asir/ Future/` | static meshes, Nanite on, collision set up |
| `Cars/<Car>/` | `SK_<Car>` skeletal mesh + skeleton + physics asset, `SM_<Car>_Body`, `SM_<Car>_Wheel_F/R` |

Materials are assigned automatically (the FBX slot names match the material instance names).
Re-running the script updates the assets in place.

> **UE 5.5+**: the script switches the FBX importer back to the classic one
> (`Interchange.FeatureFlags.Import.FBX false`) so the import options apply.

### Collision
* Landmarks, rocks, buildings and road pieces use **complex-as-simple** collision, so cars can drive
  *through* Elephant Rock's trunk arch, the Rainbow Rock arch, gates and tunnels.
* Small props (barriers, cones, tyre stacks) keep simple convex collision for cheap physics.
* Decorative pieces (lanterns, awnings, balloons, VFX meshes, cards) — set **No Collision** on the actor.

---

## 2. Lighting presets per map

Open the level you want to dress and run in the Output Log (Python mode):

```python
exec(open(r"C:/path/to/game/unreal/setup_map.py").read())
setup("riyadh")                 # riyadh | alula | jeddah | asir | future
setup("alula", showcase=True)   # also lays out every AlUla asset in a row so you can pick from them
```

| Map | Preset |
|---|---|
| Riyadh Nights | moonlight (0.4 lux, 8500 K), purple-orange city-glow fog, bloom 1.4, night exposure range |
| AlUla | golden hour, sun 7° above the horizon, warm dust haze |
| Jeddah Al-Balad | Red Sea sunset, humid haze + volumetric fog, clouds |
| Asir Mountains | misty morning: dense low height fog with volumetric fog, clouds |
| Future City | blue hour, cyan/magenta haze, strong bloom for the neon |

They are starting points — every value lives in `PRESETS` at the top of `setup_map.py`.

---

## 3. Cars with Chaos Vehicles

Each car ships as a skeletal mesh with five bones:

```
Root                (body)
 ├─ Wheel_FL   Wheel_FR
 └─ Wheel_RL   Wheel_RR
```

`assets/cars/vehicle_specs.json` (and `assets/cars/<Car>/vehicle_spec.json`) holds the exact wheel
positions, radii, widths, wheelbase, track and an arcade tuning starting point (mass, torque, rpm,
drive layout, suspension travel) for every car.

**Fastest path — reuse the Vehicle template:**
1. Add the *Vehicle* feature pack (Content Browser → Add → Add Feature or Content Pack → Vehicle), or open
   your existing car Blueprint.
2. Duplicate your car Blueprint (e.g. `BP_SportsCar_Pawn`) → `BP_Falcon`.
3. **Mesh** component → Skeletal Mesh = `SK_Falcon`.
4. **Physics asset** (`SK_Falcon_PhysicsAsset`): delete the four wheel bodies, keep one box on `Root`
   that covers the body (Chaos simulates the wheels itself).
5. **Anim Blueprint**: create one for the `SK_Falcon_Skeleton` with a *Mesh Space Ref Pose → Wheel Controller
   → Output Pose* graph (same as the template's), set it as the mesh's Anim Class.
6. **Vehicle Movement Component → Wheel Setups**: 4 entries, Bone Names `Wheel_FL`, `Wheel_FR`, `Wheel_RL`,
   `Wheel_RR`. Duplicate the template's front/rear wheel classes and set **Wheel Radius / Width** from
   `vehicle_spec.json` (e.g. Falcon front 33.5 cm / 26 cm, rear 35 cm / 32 cm). Front wheels: *Affected by
   Steering*, Max Steer Angle 40.
7. Mass, Max Torque, Max RPM and Center of Mass offset from the same JSON.

| Car | Archetype | Wheel R (F/R) | Mass | Drive |
|---|---|---|---|---|
| 01 Falcon (الصقر) | mid-engine supercar | 33.5 / 35 cm | 1350 kg | AWD |
| 02 Dune Fox (ثعلب الكثبان) | trophy truck | 48 / 48 cm | 2200 kg | AWD |
| 03 Najdi GXR (النجدي) | classic desert 4x4 | 40 / 40 cm | 2400 kg | AWD |
| 04 Hilux Raider (الغزّاي) | double-cab pickup | 38 / 38 cm | 2000 kg | RWD |
| 05 Riyadh Muscle (عضلات الرياض) | fastback muscle car | 34 / 35 cm | 1600 kg | RWD |
| 06 NEOM Glide (نيوم) | electric concept | 36 / 36 cm | 1500 kg | AWD |
| 07 AlUla Rally (رالي العُلا) | rally hatch | 33 / 33 cm | 1250 kg | AWD |
| 08 Jeddah GT (جدة جي تي) | grand tourer | 35 / 35.5 cm | 1650 kg | RWD |

**If your game uses its own (non-Chaos) arcade movement:** use the static parts instead — `SM_<Car>_Body`
at the actor root and four `SM_<Car>_Wheel_F/R` components at the wheel positions in `vehicle_spec.json`
(right-side wheels: rotate 180° in yaw). Spin the wheel components around their local Y axis.

Car materials: paint is `MI_CarNN_Paint` (clear coat) — duplicate it for colour variants. Lights are
emissive (`MI_Car_Headlight`, `MI_Car_Taillight`, `MI_Car_DRL`); raise `EmissiveStrength` on the tail
light instance while braking.

---

## 4. Cards and abilities

| Asset | Use |
|---|---|
| `T_Card_01_Falcon` … `T_Card_08_JeddahGT` | finished card fronts, one per car/character, with the car art, Arabic + English names and an ability panel. Replace the ability text with your own card text (edit `ABILITY` in `blender/card_art.py` and re-run it, or overlay UMG text). |
| `T_CardBack`, `T_CardFront_Template` | card back and an empty front template |
| `SM_Card` | 3D card (front/back UVs) — set its material to an instance with your card texture |
| `SM_CardPickup` | pickup on the track: hex pedestal + holo ring + enlarged card. Rotate/bob it in the BP. |
| `SM_VFX_Shield` | shield bubble around a car (scale 1 fits a 4.6 m car) |
| `SM_VFX_SandTornado` | sandstorm / tornado ability (spin it, use with a Niagara dust emitter) |
| `SM_VFX_NitroFlame` | exhaust flame (points along −X; attach to exhaust tips) |
| `SM_VFX_ShockRing` | EMP / shock-wave ring (scale it up over 0.5 s) |
| `SM_VFX_SandTrap` | dropped hazard on the racing line |
| `SM_FalconDrone` | homing falcon projectile (flies along +X) |
| `SM_BoostPad`, `SM_JumpRamp`, `SM_Checkpoint_Arch`, `SM_StartGantry` | track gameplay pieces |

The VFX meshes use `M_SR_VFX` (additive, unlit) — perfect for Niagara *Mesh Renderer* emitters too.

---

## 5. Performance notes

* Static meshes import with **Nanite** (except meshes with translucent glass, which the script detects).
  Hero landmarks are 15k–100k triangles; Nanite makes that free.
* Cars are ~60–75k triangles for the body + ~5–7k per wheel (skeletal meshes are not Nanite).
* Scatter palms, junipers, acacias and boulders with the **Foliage tool** (instanced) instead of placing
  thousands of actors.
* Large backdrops (`SM_AsirMountain_*`, `SM_Mesa_A`, `SM_TheLine_Segment`) are meant for the distance —
  put them in an HLOD layer or a separate streaming level.
