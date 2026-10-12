# Handoff — plug the new models into the existing Unreal project

This file is written for the Claude chat that built the Sahara Racers Unreal Engine 5 project.
The asset pack in this repo was made separately; your job is to wire it into the existing game.

**Paths (Windows):**
- Unreal project: `C:\Users\rayan\OneDrive\Desktop\racing game`
- This asset pack: wherever the user unzipped it, e.g. `C:\Users\rayan\OneDrive\Desktop\SaharaRacers_Assets`

## Before you start
1. Make a backup of the project folder (or commit it to git). Do not delete or overwrite the user's existing assets.
2. Read `README.md`, `docs/UNREAL_SETUP.md` and `docs/MAP_GUIDE.md` in the asset pack.
3. Look at the project and list:
   - the 8 characters, their cards and their abilities
   - the vehicle Blueprints
   - the 5 map levels: Riyadh Nights, AlUla, Jeddah Al-Balad, Asir mountains, Future City
4. Show the user which new car you plan to give each character. Every new car is listed in
   `assets/cars/vehicle_specs.json`.

## Steps
1. **Import:** enable the *Python Editor Script Plugin*. Open `unreal/import_assets.py` and set `REPO` to the
   asset-pack folder if the script can't find it. Run it with Tools → Execute Python Script.
   Everything lands in `/Game/SaharaRacers/`.
2. **Cars (one at a time, play-test after each):**
   - Duplicate the character's vehicle Blueprint and set its mesh to `SK_<Car>`.
   - In the physics asset, keep only the `Root` body and delete the 4 wheel bodies.
   - Add an Anim Blueprint with *Wheel Controller* for the new skeleton.
   - Set the wheel setups to bones `Wheel_FL`, `Wheel_FR`, `Wheel_RL` and `Wheel_RR`. Take the radius, width,
     mass, torque and rpm from `assets/cars/<Car>/vehicle_spec.json`.
   - If the game does not use Chaos vehicles, use `SM_<Car>_Body` plus the `SM_<Car>_Wheel_F/R` static meshes instead.
3. **Maps:** open each level and run `unreal/setup_map.py`, then call
   `setup("riyadh" | "alula" | "jeddah" | "asir" | "future")` for its lighting. Replace the old placeholder
   buildings and rocks with the kit landmarks, keeping the existing track and gameplay. Follow
   `docs/MAP_GUIDE.md`: Kingdom Centre and Al Faisaliah on the Riyadh skyline, Elephant Rock and the Hegra tomb
   in AlUla, rawasheen houses in Jeddah, and so on.
4. **Cards and abilities:** put the `T_Card_01..08` textures on the matching characters' cards. Each card's
   ability text is a placeholder, so keep the game's real card text (edit `ABILITY` in `blender/card_art.py`
   and re-run it if needed). Use the `SM_VFX_*` meshes and `SM_FalconDrone` for the ability effects,
   `SM_CardPickup` for pickups, and `SM_Checkpoint_Arch` and `SM_StartGantry` for the track.
5. Save, play-test every map, and report what changed to the user.

The import scripts were written without access to Unreal, so expect small API fixes on the first run.
If a property name errors, fix it and continue.
