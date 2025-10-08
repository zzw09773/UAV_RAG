"""DATCOM Parameter Calculation Tools.

This module provides a set of tools for converting standard aircraft design
parameters into the specific formats required by the DATCOM software.

Design Philosophy:
- No special cases: Unified calculation logic for all lifting surfaces.
- Data-structure first: Clear input/output mappings.
- Non-destructive: Fully compatible with existing tools.
"""
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.tools import tool
import math
from ..common import log


# ============================================================================
# Core Calculation Functions (Pure Functions)
# ============================================================================

def calculate_wingspan(S: float, A: float) -> float:
    """Calculates wingspan: b = sqrt(A * S)"""
    return math.sqrt(A * S)


def calculate_root_chord(S: float, b: float, lambda_: float) -> float:
    """Calculates root chord: Croot = 2S / [b(1+λ)]"""
    return (2 * S) / (b * (1 + lambda_))


def calculate_tip_chord(Croot: float, lambda_: float) -> float:
    """Calculates tip chord: Ctip = λ * Croot"""
    return lambda_ * Croot


def calculate_mean_aerodynamic_chord(Croot: float, lambda_: float) -> float:
    """Calculates Mean Aerodynamic Chord (MAC)"""
    return (2/3) * Croot * (1 + lambda_ + lambda_**2) / (1 + lambda_)


def calculate_aspect_ratio(b: float, S: float) -> float:
    """Calculates aspect ratio: A = b^2/S"""
    return (b ** 2) / S


def calculate_taper_ratio(Ctip: float, Croot: float) -> float:
    """Calculates taper ratio: λ = Ctip/Croot"""
    return Ctip / Croot


# ============================================================================
# DATCOM Parameter Conversion Tools (LangChain Tools)
# ============================================================================

@tool
def convert_wing_to_datcom(
    S: float,
    A: float,
    lambda_: float,
    sweep_angle: float,
    airfoil: str = "2412",
    dihedral: float = 0.0,
    twist: float = 0.0,
    sweep_location: float = 0.0
) -> Dict[str, Any]:
    """Converts standard wing parameters (area, aspect ratio, taper ratio, sweep) to DATCOM's $WGPLNF namelist format.

    Args:
        S: Wing reference area (ft²).
        A: Aspect ratio.
        lambda_: Taper ratio (0.0 to 1.0).
        sweep_angle: Sweep angle (degrees).
        airfoil: (Optional) NACA airfoil designation. Defaults to "2412".
        dihedral: (Optional) Dihedral angle (degrees). Defaults to 0.0.
        twist: (Optional) Twist angle (degrees, negative for washout). Defaults to 0.0.
        sweep_location: (Optional) Chordwise location for sweep measurement (percent). Defaults to 0.0.

    Returns:
        A dictionary containing DATCOM $WGPLNF parameters.
    """
    log(f"Converting wing params: S={S}, A={A}, λ={lambda_}, sweep={sweep_angle}°")
    
    if S <= 0 or A <= 0:
        return {"error": "Wing area (S) and aspect ratio (A) must be greater than 0."}
    if not (0 <= lambda_ <= 1):
        return {"error": f"Taper ratio (lambda_) must be between 0 and 1, but got {lambda_}."}
    
    b = calculate_wingspan(S, A)
    Croot = calculate_root_chord(S, b, lambda_)
    Ctip = calculate_tip_chord(Croot, lambda_)
    SSPN = b / 2
    MAC = calculate_mean_aerodynamic_chord(Croot, lambda_)
    
    datcom_params = {
        "CHRDR": round(Croot, 2),
        "CHRDTP": round(Ctip, 2),
        "SSPN": round(SSPN, 2),
        "SSPNE": round(SSPN, 2),
        "SAVSI": round(sweep_angle, 1),
        "CHSTAT": sweep_location,
        "TYPE": 1.0,
        "DHDADI": round(dihedral, 1),
        "TWISTA": round(twist, 1),
        "airfoil": f"NACA-W-4-{airfoil}",
        "SREF": round(S, 2),
        "_wingspan": round(b, 2),
        "_MAC": round(MAC, 2),
        "_aspect_ratio": round(A, 2),
        "_taper_ratio": round(lambda_, 3),
        "_formulas": {
            "wingspan": f"b = √({A}·{S}) = {b:.2f} ft",
            "root_chord": f"Croot = 2·{S} / [{b:.2f}·(1+{lambda_})] = {Croot:.2f} ft",
            "tip_chord": f"Ctip = {lambda_}·{Croot:.2f} = {Ctip:.2f} ft",
            "semi_span": f"SSPN = {b:.2f}/2 = {SSPN:.2f} ft",
            "MAC": f"MAC = (2/3)·{Croot:.2f}·(1+{lambda_}+{lambda_**2:.3f})/(1+{lambda_}) = {MAC:.2f} ft"
        }
    }
    
    log(f"✓ Wing conversion complete: SSPN={SSPN:.2f}, CHRDR={Croot:.2f}, CHRDTP={Ctip:.2f}")
    return datcom_params


@tool
def convert_tail_to_datcom(
    component: str,
    S: float,
    A: float,
    lambda_: float,
    sweep_angle: float,
    airfoil: str = "0012",
    is_vertical: bool = False
) -> Dict[str, Any]:
    """Converts tail surface parameters (area, aspect ratio, taper ratio, sweep) to DATCOM's $HTPLNF or $VTPLNF namelist format.

    Args:
        component: The component name ("horizontal_tail" or "vertical_tail").
        S: Tail surface area (ft²).
        A: Aspect ratio.
        lambda_: Taper ratio.
        sweep_angle: Sweep angle (degrees).
        airfoil: (Optional) NACA airfoil designation. Defaults to "0012".
        is_vertical: (Optional) Set to True for a vertical tail. Defaults to False.

    Returns:
        A dictionary containing DATCOM $HTPLNF or $VTPLNF parameters.
    """
    log(f"Converting {component}: S={S}, A={A}, λ={lambda_}, sweep={sweep_angle}°")
    
    if S <= 0 or A <= 0:
        return {"error": "Area (S) and aspect ratio (A) must be greater than 0."}
    if not (0 <= lambda_ <= 1):
        return {"error": f"Taper ratio (lambda_) must be between 0 and 1, but got {lambda_}."}
    
    b = calculate_wingspan(S, A)
    Croot = calculate_root_chord(S, b, lambda_)
    Ctip = calculate_tip_chord(Croot, lambda_)
    SSPN = b / 2
    
    namelist = "$VTPLNF" if is_vertical else "$HTPLNF"
    airfoil_prefix = "V" if is_vertical else "H"
    
    datcom_params = {
        "CHRDR": round(Croot, 2),
        "CHRDTP": round(Ctip, 2),
        "SSPN": round(SSPN, 2),
        "SSPNE": round(SSPN, 2),
        "SAVSI": round(sweep_angle, 1),
        "CHSTAT": 0.0,
        "TYPE": 1.0,
        "DHDADI": 0.0,
        "TWISTA": 0.0,
        "airfoil": f"NACA-{airfoil_prefix}-4-{airfoil}",
        "_component": component,
        "_namelist": namelist,
        "_wingspan_or_height": round(b, 2),
        "_area": round(S, 2),
        "_formulas": {
            "dimension": f"b = √({A}·{S}) = {b:.2f} ft {'(height)' if is_vertical else '(span)'}",
            "root_chord": f"Croot = 2·{S} / [{b:.2f}·(1+{lambda_})] = {Croot:.2f} ft",
            "tip_chord": f"Ctip = {lambda_}·{Croot:.2f} = {Ctip:.2f} ft",
            "SSPN": f"SSPN = {b:.2f}/2 = {SSPN:.2f} ft"
        }
    }
    
    log(f"✓ {component} conversion complete: SSPN={SSPN:.2f}, CHRDR={Croot:.2f}")
    return datcom_params


@tool
def calculate_synthesis_positions(
    fuselage_length: float,
    wing_position_percent: float = 0.40,
    htail_position_percent: float = 0.90,
    vtail_position_percent: float = 0.65,
    cg_position_percent: float = 0.35,
    wing_z: float = 0.0,
    htail_z: float = 0.0,
    vtail_z: float = 0.0
) -> Dict[str, Any]:
    """Calculates component X,Z coordinates for the DATCOM $SYNTHS namelist.

    Args:
        fuselage_length: Total fuselage length (ft).
        wing_position_percent: (Optional) Wing apex position as a percentage of fuselage length. Defaults to 0.40.
        htail_position_percent: (Optional) Horizontal tail position. Defaults to 0.90.
        vtail_position_percent: (Optional) Vertical tail position. Defaults to 0.65.
        cg_position_percent: (Optional) Center of Gravity position. Defaults to 0.35.
        wing_z: (Optional) Wing vertical position (ft). Defaults to 0.0.
        htail_z: (Optional) Horizontal tail vertical position (ft). Defaults to 0.0.
        vtail_z: (Optional) Vertical tail vertical position (ft). Defaults to 0.0.

    Returns:
        A dictionary containing DATCOM $SYNTHS parameters.
    """
    log(f"Calculating $SYNTHS positions for fuselage length={fuselage_length} ft")
    
    if fuselage_length <= 0:
        return {"error": "Fuselage length must be greater than 0."}
    
    XCG = fuselage_length * cg_position_percent
    XW = fuselage_length * wing_position_percent
    XH = fuselage_length * htail_position_percent
    XV = fuselage_length * vtail_position_percent
    
    synths_params = {
        "XCG": round(XCG, 2),
        "ZCG": 0.0,
        "XW": round(XW, 2),
        "ZW": round(wing_z, 2),
        "ALIW": 1.0,
        "XH": round(XH, 2),
        "ZH": round(htail_z, 2),
        "ALIH": 0.0,
        "XV": round(XV, 2),
        "ZV": round(vtail_z, 2),
        "_fuselage_length": fuselage_length,
        "_positions_percent": {
            "CG": f"{cg_position_percent*100:.1f}%",
            "Wing": f"{wing_position_percent*100:.1f}%",
            "HTail": f"{htail_position_percent*100:.1f}%",
            "VTail": f"{vtail_position_percent*100:.1f}%"
        },
        "_moment_arms": {
            "wing_to_cg": round(XW - XCG, 2),
            "htail_to_cg": round(XH - XCG, 2),
            "vtail_to_cg": round(XV - XCG, 2)
        }
    }
    
    log(f"✓ $SYNTHS calculated: XCG={XCG:.2f}, XW={XW:.2f}, XH={XH:.2f}, XV={XV:.2f}")
    return synths_params


@tool
def define_body_geometry(
    x_coords: List[float],
    zu_coords: List[float],
    zl_coords: List[float],
    method: int = 1
) -> Dict[str, Any]:
    """Defines the fuselage geometry for the DATCOM $BODY namelist using coordinate arrays.

    Args:
        x_coords: List of longitudinal (X) station coordinates.
        zu_coords: List of upper surface (ZU) Z-coordinates at each station.
        zl_coords: List of lower surface (ZL) Z-coordinates at each station.
        method: (Optional) Aerodynamic method for calculation. Defaults to 1.

    Returns:
        A dictionary containing DATCOM $BODY parameters.
    """
    log(f"Defining $BODY with {len(x_coords)} coordinate pairs.")
    
    if not (len(x_coords) == len(zu_coords) == len(zl_coords)):
        return {"error": "Input coordinate lists (x_coords, zu_coords, zl_coords) must have the same length."}
    if len(x_coords) > 20:
        return {"error": "DATCOM supports a maximum of 20 fuselage stations."}

    # Calculate radius R for informational purposes, assuming ZU = -ZL for symmetric sections
    # This is a simplification; for true non-axisymmetric bodies, ZU and ZL are the primary inputs.
    R_stations = [round((zu - zl) / 2, 3) for zu, zl in zip(zu_coords, zl_coords)]

    body_params = {
        "NX": float(len(x_coords)),
        "X": x_coords,
        "ZU": zu_coords,
        "ZL": zl_coords,
        "R": R_stations, # For reference, not directly used by DATCOM if ZU/ZL are present
        "METHOD": method,
        "ITYPE": 1, # Assuming a standard body type
    }
    
    log(f"✓ $BODY defined with {body_params['NX']} stations.")
    return body_params


@tool
def generate_fltcon_matrix(
    mach_numbers: List[float],
    altitudes: List[float],
    alpha_range: List[float],
    weight: float,
    loop_mode: float = 2.0
) -> Dict[str, Any]:
    """Generates the flight condition matrix for the DATCOM $FLTCON namelist.

    Args:
        mach_numbers: A list of Mach numbers.
        altitudes: A list of altitudes (ft).
        alpha_range: A list of three values [start, end, step] for angle of attack in degrees.
        weight: Aircraft weight (lbs).
        loop_mode: (Optional) Loop mode for analysis. Defaults to 2.0 (Mach-priority).

    Returns:
        A dictionary containing DATCOM $FLTCON parameters.
    """
    log(f"Generating $FLTCON: M={mach_numbers}, ALT={altitudes}")
    
    if len(alpha_range) != 3:
        return {"error": "alpha_range must contain exactly 3 values: [start, end, step]"}
    
    alpha_start, alpha_end, alpha_step = alpha_range
    alpha_schedule = []
    alpha = alpha_start
    while alpha <= alpha_end:
        alpha_schedule.append(round(alpha, 1))
        alpha += alpha_step
    
    if len(alpha_schedule) > 20:
        return {"error": "DATCOM supports a maximum of 20 angles of attack (NALPHA <= 20)."}
    
    fltcon_params = {
        "NMACH": float(len(mach_numbers)),
        "MACH": [round(m, 2) for m in mach_numbers],
        "NALT": float(len(altitudes)),
        "ALT": [round(alt, 1) for alt in altitudes],
        "NALPHA": float(len(alpha_schedule)),
        "ALSCHD": alpha_schedule,
        "WT": round(weight, 1),
        "LOOP": float(loop_mode),
        "_analysis_points": len(mach_numbers) * len(altitudes) * len(alpha_schedule),
        "_loop_description": {
            1.0: "For each altitude, loop through all alphas and Machs.",
            2.0: "For each Mach, loop through all altitudes and alphas.",
            3.0: "For each altitude, loop through all Machs and alphas."
        }.get(loop_mode, "Unknown loop mode")
    }
    
    log(f"✓ $FLTCON generated: {fltcon_params['_analysis_points']} analysis points")
    return fltcon_params


@tool
def validate_datcom_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the reasonableness and consistency of a dictionary of DATCOM parameters.

    Args:
        params: A dictionary containing various DATCOM parameters from other tools.

    Returns:
        A validation report with a status, and lists of errors and warnings.
    """
    log("Validating DATCOM parameters...")
    
    warnings = []
    errors = []
    
    if 'CHRDR' in params and 'CHRDTP' in params:
        if params['CHRDTP'] > params['CHRDR']:
            errors.append("Tip chord (CHRDTP) should not be greater than root chord (CHRDR).")
    
    if 'SSPN' in params and 'SSPNE' in params:
        if params['SSPNE'] > params['SSPN']:
            errors.append("Exposed semi-span (SSPNE) should not be greater than theoretical semi-span (SSPN).")
    
    if 'SAVSI' in params:
        if abs(params['SAVSI']) > 70:
            warnings.append(f"Sweep angle of {params['SAVSI']}° is outside the typical range (±70°).")
    
    if 'DHDADI' in params:
        if abs(params['DHDADI']) > 15:
            warnings.append(f"Dihedral angle of {params['DHDADI']}° is outside the typical range (±15°).")
    
    for key, value in params.items():
        if isinstance(value, int) and not key.startswith('_'):
            warnings.append(f"Parameter {key}={value} should be a float (e.g., {float(value)}).")
    
    validation_report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "checked_parameters": list(params.keys()),
        "summary": f"{len(errors)} errors, {len(warnings)} warnings."
    }
    
    log(f"✓ Validation complete: {validation_report['summary']}")
    return validation_report


# ============================================================================
# Toolset Export
# ============================================================================

def create_datcom_calculator_tools() -> List:
    """Creates the complete DATCOM calculator toolset."""
    return [
        convert_wing_to_datcom,
        convert_tail_to_datcom,
        calculate_synthesis_positions,
        define_body_geometry,
        generate_fltcon_matrix,
        validate_datcom_parameters
    ]


if __name__ == "__main__":
    # Test Example: F-4 Phantom II
    print("=" * 80)
    print("DATCOM Calculator Tool Test - F-4 Phantom II")
    print("=" * 80)
    
    wing = convert_wing_to_datcom.invoke({
        "S": 530,
        "A": 2.8,
        "lambda_": 0.3,
        "sweep_angle": 45,
        "dihedral": -3.0
    })
    print("\n1. Wing Parameters ($WGPLNF):")
    for k, v in wing.items():
        if not k.startswith('_'):
            print(f"  {k} = {v}")
    
    htail = convert_tail_to_datcom.invoke({
        "component": "horizontal_tail",
        "S": 100,
        "A": 3.0,
        "lambda_": 0.4,
        "sweep_angle": 35
    })
    print("\n2. Horizontal Tail ($HTPLNF):")
    for k, v in htail.items():
        if not k.startswith('_'):
            print(f"  {k} = {v}")
    
    fltcon = generate_fltcon_matrix.invoke({
        "mach_numbers": [0.6, 0.8, 0.95],
        "altitudes": [10000, 20000, 30000],
        "alpha_range": [-4, 14, 2],
        "weight": 38000,
        "loop_mode": 2
    })
    print("\n3. Flight Conditions ($FLTCON):")
    print(f"  Analysis Points: {fltcon['_analysis_points']}")
    print(f"  Mach: {fltcon['MACH']}")
    print(f"  Altitudes: {fltcon['ALT']}")
    
    print("\n" + "=" * 80)
    print("✓ All tests completed successfully!")