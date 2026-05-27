# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

DSSAT-CSM-OS is the open-source **DSSAT Cropping System Model** (v4.8.5) — a Fortran-based crop simulation framework that models growth, development, and yield of 45+ crops as a function of soil-plant-atmosphere dynamics. The codebase is ~543 Fortran source files (460 legacy `.for` fixed-form + 78 modern `.f90` free-form).

## Build Commands

Out-of-source builds are required (in-source builds are blocked by CMake):

```bash
mkdir build && cd build

# Debug build (default if no type specified) — bounds checking, full traceback, -Og
cmake .. -DCMAKE_BUILD_TYPE=DEBUG

# Release build — -O3, loop unrolling, inline functions
cmake .. -DCMAKE_BUILD_TYPE=RELEASE

# Testing build — -O2
cmake .. -DCMAKE_BUILD_TYPE=TESTING

make
```

The executable is placed at `build/bin/dscsm048`. Fortran `.mod` files go to `build/mod/`.

**Specifying a compiler:**
```bash
cmake -G "Unix Makefiles" -DCMAKE_Fortran_COMPILER=ifort ..
```

**Cleaning the build:**
```bash
cmake -P distclean.cmake   # from repo root
# or, inside the build directory:
make distclean
```

**Dynamic linking** (static by default):
```bash
cmake .. -DDYNAMIC_LINK=ON
```

## Running the Model

```bash
# Run a single simulation (Mode C = single treatment, Mode A = all treatments)
./build/bin/dscsm048 C UFGA8201.MZX 1

# Arguments: <mode> <batch-file> [treatment-number]
# The working directory must contain the experiment/batch file and supporting data
```

The working directory for a run must contain the experiment file (`.MZX`, `.WHX`, etc.), soil profiles, weather data, and genotype files. Batch files live in `Data/BatchFiles/`.

## Architecture

### Data Flow

```
Input files → INTRO (InputModule) → CSM (entry point)
                                      └─ LAND (land unit controller)
                                           ├─ WEATHR  (weather data)
                                           ├─ SOIL    (soil processes)
                                           ├─ SPAM    (soil-plant-atmosphere)
                                           ├─ PLANT   (crop dispatcher → individual crop models)
                                           └─ MGMTOPS (management: irrigation, fertilizer, tillage)
```

### Key Source Files

- **`CSM_Main/CSM.for`** — Program entry point. Parses command-line args, manages simulation loops (single/sequence runs), calls `LAND`.
- **`CSM_Main/LAND.for`** — Land unit controller. Orchestrates per-timestep calls to all sub-modules (WEATHR, SOIL, SPAM, PLANT, MGMTOPS). Handles variable exchange between modules.
- **`Plant/plant.for`** — Crop model dispatcher. Routes to the correct crop-specific subroutine based on the `MODEL` variable (e.g., `MZ_CERES` for maize, `CROPGRO` for legumes).
- **`Utilities/ModuleDefs.for`** — Central hub: defines all shared Fortran derived types (`SoilType`, `WeatherType`, `SwitchType`, `ControlType`, etc.) and global constants (`NL=20` soil layers, `NAPPL=9000` max applications, `NELEM=3`).
- **`Utilities/CSMVersion.for.in`** — Template file; CMake generates `CSMVersion.for` with the actual version/commit info at configure time. Do not edit `CSMVersion.for` directly.

### Module Execution Pattern

Every major subroutine uses a `DYNAMIC` integer flag to distinguish lifecycle phases:

```fortran
RUNINIT  = 1   ! First call, run-level initialization
SEASINIT = 2   ! Seasonal initialization (start of each growing season)
RATE     = 3   ! Daily rate calculations
INTEGR   = 4   ! Integration of rates into state variables
OUTPUT   = 5   ! Write output for the day
SEASEND  = 6   ! End-of-season processing
ENDRUN   = 7   ! End-of-run cleanup
```

All major subroutines receive `CONTROL` and `ISWITCH` as the first two arguments. `CONTROL` carries run metadata (dates, file paths, mode); `ISWITCH` carries simulation switches (what processes to simulate).

### Crop Models

Individual crop models live in `Plant/<ModelName>/`. The naming convention encodes the model:
- `MZ_*` — CERES-Maize
- `CROPGRO` — Legumes (soybean, peanut, drybean, etc.) — uses species/ecotype/cultivar files
- `SC_*` — CANEGRO Sugarcane
- `CSP_*` — CASUPRO Sugarcane
- `RI_*` — CERES-Rice
- `ML_*` — CERES-Millet
- `PT_*` — SUBSTOR-Potato
- `CS_*` — CROPSIM/CSCAS (cassava, wheat/barley)

### Soil Module

`Soil/SOIL.for` dispatches to sub-modules in `Soil/`:
- `SoilWater/` — water balance
- `Inorganic_N/` — nitrogen cycling
- `Inorganic_P/` — phosphorus
- `Inorganic_K/` — potassium
- `CENTURY_OrganicMatter/` or `CERES_OrganicMatter/` — SOM decomposition
- `FloodN/` — flooded/paddy conditions
- `GHG/` — greenhouse gas emissions

### OS-Specific Code

- **`Utilities/OSDefsLINUX.for`** — Linux (selected at configure time)
- **`Utilities/OSDefsWINDOWS.for`** — Windows

CMake selects the appropriate file via the `OSDefinitions` variable; never include both in a build.

### CMake-Generated Files

The following files are auto-generated at configure time — edit the `.in` templates, not the output:
- `Utilities/CSMVersion.for` ← `Utilities/CSMVersion.for.in`
- `Data/DSSATPRO.L48` ← `Data/DSSATPRO.L48.in`
- `Utilities/run_dssat` ← `Utilities/run_dssat.in`

## Data Directory

`Data/` contains model-specific data required at runtime (not source code):
- `*.CDE` files — Code Definition Exchange files that map variable codes to descriptions and units
- `Genotype/` — cultivar/ecotype coefficient files per crop (e.g., `MZCER048.CUL` for maize)
- `Pest/` — pest and disease model parameters
- `StandardData/` — global reference data
- `DSSATPRO.v48` / `DSSATPRO.L48` — DSSAT profile pointing to data directories
- `DSCSM048.CTR` — default simulation control file template

Experimental datasets (soil profiles, weather files, field experiment files) are maintained in a separate repository: https://github.com/DSSAT/dssat-csm-data.

## Coding Conventions

The project follows [DSSAT Fortran Coding Guidelines](https://dssat.net/non-threatening-best-practice-dssat-fortran-coding-guidelines).

- Legacy files use Fortran 77 fixed-form (`.for`, 72-column lines extended to 132 via compiler flag). New code should use free-form Fortran 90+ (`.f90`).
- `IMPLICIT NONE` is used in all modern modules.
- Revision history blocks at the top of each file follow the pattern `! YYYY-MM-DD INITIALS Description`.
- All shared derived types are defined in `ModuleDefs.for` — add new types there, not in individual modules.
- Output files (`.OUT`, `.LST`, `.csv`) are gitignored; never commit them.

## Version Numbering

Version is `MAJOR.MINOR.MODEL.BUILD` (currently `4.8.5.41`). Set in `CMakeLists.txt`:
```cmake
SET(MAJOR 4)
SET(MINOR 8)
SET(MODEL 5)
SET(BUILD 41)
```
The executable name derives from `MAJOR` and `MINOR`: `dscsm048`. Increment `BUILD` for patch releases.
