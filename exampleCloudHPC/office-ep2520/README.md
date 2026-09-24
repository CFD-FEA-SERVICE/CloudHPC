# office-ep2520 — EnergyPlus 25.2.0 · single-zone office

An 80 m² open-plan office in Rome — one thermal zone, 10 × 8 × 3 m, with a
12 m² window on the south façade — served by an ideal-loads air system with a
dual heating/cooling setpoint. People, lighting, equipment and infiltration are
scheduled for a weekday office profile.

The model runs on **sizing periods only**: a winter and a summer design day. That
makes the folder completely self-contained — no `.epw` weather file to find,
licence or upload — and the whole simulation finishes in well under a second,
which is exactly what you want from a first job on a new account.

## Case at a glance

| | |
|---|---|
| Solver script | `EnergyPlus-25.2.0` |
| Suggested vCPU / RAM | 1 / `standard` |
| Zone | 80 m², 240 m³, one zone, 12 m² south glazing (U = 1.6 W/m²K, SHGC = 0.4) |
| Gains | 8 people, 8 W/m² lighting, 10 W/m² equipment, 0.3 ACH infiltration |
| Setpoints | 20 °C heating / 26 °C cooling during occupied hours |
| Weather | two design days (21 Jan at 0 °C, 21 Jul at 33 °C), no weather file |
| Indicative runtime | ~0.15 s |
| Source | written for this repository — see [Source and credits](#source-and-credits) |

EnergyPlus is single-threaded, so one vCPU is the right ask. Parallelism on this
platform comes from launching many parametric variants at once, not from
throwing cores at one model.

## Files

| File | Purpose |
|---|---|
| `office.idf` | the complete model — geometry, constructions, schedules, gains, HVAC and outputs |

The `EnergyPlus-25.2.0` script picks up the `.idf` in the folder. If you later
add a weather file, drop the `.epw` in the same folder.

## Run it on cloudhpc.cloud

A single file, so no compression is needed.

1. **STORAGE → Add**: type `office-ep2520` in the *Dirname* text box, drop
   `office.idf` in the *File* box, press **Save**.
2. **SIMULATIONS → Add**:
   - **vCPU** `1`
   - **RAM** `standard`
   - **Folder** `office-ep2520`
   - **Script** `EnergyPlus-25.2.0`
3. **Save**, then download the results from **STORAGE**.

## Run it with cloudHPCexec

```bash
cd office-ep2520

cloudHPCexec                                                 # interactive menus
cloudHPCexec -batch 1 standard EnergyPlus-25.2.0 office-ep2520
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

## What to expect

The run completes with **0 warnings and 0 severe errors**, and sizes the zone at

| Load | Peak | Design day | Time of peak |
|---|---|---|---|
| Cooling | 1 502 W (18.8 W/m²) | Rome summer | 21 Jul, 15:10 |
| Heating | 2 954 W (36.9 W/m²) | Rome winter | 21 Jan, 08:00 |

Output files:

| File | Contains |
|---|---|
| `eplustbl.htm` | the tabular summary reports — open this first |
| `eplusout.csv` | hourly zone temperature, humidity, heating/cooling rates, outdoor temperature |
| `eplusout.err` | the warning/error log — always read it, even on a successful run |
| `eplusout.eio` | the sizing results quoted above |
| `eplusout.sql` | SQLite database of every reported variable |

## Running a full year

Design days size the equipment; they do not give you annual energy. To run a
full year:

1. Download an `.epw` for your site (for example from the EnergyPlus weather
   database) and upload it into the same storage folder.
2. Add a `RunPeriod` object to the `.idf`.
3. In `SimulationControl`, set *Run Simulation for Weather File Run Periods* to
   `Yes`.

## A note on EnergyPlus versions

The platform carries `EnergyPlus-9.4.0`, `EnergyPlus-9.6.0` and
`EnergyPlus-25.2.0`. EnergyPlus is unusually strict about this: the `Version`
object at the top of the `.idf` must match the executable, and the input schema
changes at nearly every release — objects gain fields, and some are renamed or
retired. An `.idf` written for 9.6 will **not** run unchanged on 25.2.

To move a model forward, run the `IDFVersionUpdater` shipped with EnergyPlus
locally, then upload the converted file. Going the other way is not supported —
keep the original.


## Source and credits

`office.idf` was **written for this repository**; it is not a copy of an
upstream example file. It is assembled from the standard object set described in
the EnergyPlus Input Output Reference — a single zone, detailed surfaces,
compact schedules, an ideal-loads air system and design-day sizing — and was
verified by running it with EnergyPlus 25.2.0 (0 warnings, 0 severe errors).

| | |
|---|---|
| Solver | EnergyPlus, developed by NREL for the U.S. Department of Energy |
| Home page | [energyplus.net](https://energyplus.net/) |
| Source code | [github.com/NREL/EnergyPlus](https://github.com/NREL/EnergyPlus) |
| Licence | [BSD-style, 3-clause](https://github.com/NREL/EnergyPlus/blob/develop/LICENSE.txt) |
| Object reference | [Input Output Reference](https://bigladdersoftware.com/epx/docs/25-2/input-output-reference/) |

EnergyPlus ships several hundred `ExampleFiles/*.idf` with the installation,
which are the right place to look for a richer model — multi-zone geometry, real
HVAC plant, daylighting — than the single zone used here.
