# DATCOM Tools: Developer Notes

This document provides technical notes on the implementation of the DATCOM parameter calculation and conversion toolset.

## 1. Implemented Tools

The toolset is located in `rag_system/tool/datcom_calculator.py` and consists of six main functions decorated with `@tool`.

1.  **`convert_wing_to_datcom`**
    -   **Purpose**: Converts standard wing parameters into a DATCOM `$WGPLNF` namelist.
    -   **Inputs**: `S` (area), `A` (aspect ratio), `lambda_` (taper ratio), `sweep_angle`, and optional `airfoil`, `dihedral`, `twist`.
    -   **Core Formulas**: `b = sqrt(A*S)`, `Croot = 2S / [b(1+λ)]`, `Ctip = λ*Croot`.
    -   **Output**: A dictionary containing `CHRDR`, `CHRDTP`, `SSPN`, `SAVSI`, etc.

2.  **`convert_tail_to_datcom`**
    -   **Purpose**: Converts tail surface parameters to `$HTPLNF` or `$VTPLNF` namelists.
    -   **Inputs**: `component` (name), `S`, `A`, `lambda_`, `sweep_angle`, `is_vertical`.
    -   **Logic**: Reuses the same core calculation functions as the wing converter.

3.  **`calculate_synthesis_positions`**
    -   **Purpose**: Computes component coordinates for the `$SYNTHS` namelist.
    -   **Inputs**: `fuselage_length` and percentage-based positions for wing, tail, and CG.
    -   **Output**: `XCG`, `XW`, `XH`, `XV`, and their corresponding Z-coordinates.

4.  **`define_body_geometry`**
    -   **Purpose**: Defines an axisymmetric fuselage for the `$BODY` namelist.
    -   **Inputs**: `fuselage_length`, `max_diameter`, `nose_length`, `tail_length`, `num_stations`.
    -   **Output**: `NX`, `X`, `R`, and `S` arrays for DATCOM.

5.  **`generate_fltcon_matrix`**
    -   **Purpose**: Generates the flight condition matrix for the `$FLTCON` namelist.
    -   **Inputs**: `mach_numbers`, `altitudes`, `alpha_range`, `weight`.
    -   **Output**: `NMACH`, `MACH`, `NALT`, `ALT`, `NALPHA`, `ALSCHD`, etc.

6.  **`validate_datcom_parameters`**
    -   **Purpose**: Performs a sanity check on a dictionary of DATCOM parameters.
    -   **Checks**: Geometric consistency (e.g., `CHRDTP <= CHRDR`), range checks (e.g., `abs(sweep) <= 70`), and FORTRAN format suggestions (e.g., `5.0` instead of `5`).

## 2. Design Philosophy

-   **No Special Cases**: All lifting surfaces (wing, h-tail, v-tail) share the same core geometric calculation functions (`calculate_wingspan`, `calculate_root_chord`, etc.). This reduces code duplication and improves maintainability.

-   **Data-Structure First**: The tools are designed around clear input/output dictionaries, mapping standard engineering parameters to their DATCOM equivalents. This avoids complex conditional logic.

-   **Traceability**: The output dictionaries include a `_formulas` key that shows the exact calculations performed. This is invaluable for debugging and verification.

## 3. Testing

Unit tests are located in `test_datcom_calculator.py`. The tests cover:
-   Full parameter calculation for an F-4 Phantom II example.
-   Consistency validation against a MiG-17 example.
-   Boundary conditions and error handling.

To run the tests, use `pytest`.
