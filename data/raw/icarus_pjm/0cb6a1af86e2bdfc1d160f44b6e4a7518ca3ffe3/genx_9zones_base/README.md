# PJM 9 Zone Model

This repository provides a **GenX-formatted PJM 9 Zone Model**. It is adapted from GenX’s [`1_three_zones` example](https://www.google.com/search?q=%5Bhttps://github.com/GenXProject/GenX.jl/tree/main/example_systems/1_three_zones%5D\(https://github.com/GenXProject/GenX.jl/tree/main/example_systems/1_three_zones\)) and updated with data from the [ICARUS PJM Data](https://github.com/HopkinsICARUS/ICARUS-PJM-Dataset/tree/main/data/PJM). Where ICARUS data was unavailable, default GenX values are retained.

## Key Components

### VRE Resources (`resources/Vre.csv`)

  * Existing wind and solar generators are aggregated by PJM region and state, then split into RES and resource classes.
  * Default `Inv_Cost_per_MWyr` and `Fixed_OM_Cost_per_MWyr` values are retained from GenX.
  * Offshore wind costs are scaled relative to onshore costs: **3×** for fixed-bottom and **5×** for floating.

### Generation Profiles (`system/Generators_variability.csv`)

  * This file provides detailed variability profiles for VRE.
  * Thermal generators are assigned a default variability of 1 (assuming they are fully dispatchable).
  * The `PJM_ATSI_PA_SolarPV` profile, which was missing from the raw data, has been replaced with the `PJM_ATSI_OH_SolarPV` profile.

### Demand Profiles

  * Base load profiles are sourced from the EPA.

### Storage (`resources/Storage.csv`)

  * Combines batteries and pumped hydro, consistent with GenX conventions.

### Emissions (`system/Fuels_data.csv`)

  * Provides constant and fuel-specific emission factors.
  * For simplicity, multiple-fuel capability for generators is ignored.

### Transmission Interfaces

  * This version does not explicitly model cross-regional transmission interfaces.
  * These flows can be approximated by representing outgoing flows as generators (see `data/processed/PJM/generators_interface.csv`) and incoming flows as loads (see `data/processed/PJM/loads_interface.csv`).