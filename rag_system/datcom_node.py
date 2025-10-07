"""
Node for executing a fixed sequence of DATCOM tool calls.
"""
import json
import math
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .state import GraphState
from .common import log
from .tool import create_datcom_calculator_tools

# --- Parameter Extraction ---

class DatcomParams(BaseModel):
    """Schema for all possible DATCOM parameters extracted from a user query."""
    wing_S: Optional[float] = Field(None, description="Wing reference area (S)")
    wing_A: Optional[float] = Field(None, description="Wing aspect ratio (A)")
    wing_lambda: Optional[float] = Field(None, description="Wing taper ratio (λ)")
    wing_sweep_angle: Optional[float] = Field(None, description="Wing sweep angle at quarter-chord")
    
    # Horizontal tail parameters
    htail_S: Optional[float] = Field(None, description="Horizontal tail area (S)")
    htail_A: Optional[float] = Field(None, description="Horizontal tail aspect ratio (A)")
    htail_lambda: Optional[float] = Field(None, description="Horizontal tail taper ratio (λ)")
    htail_sweep_angle: Optional[float] = Field(None, description="Horizontal tail sweep angle")
    
    # Vertical tail parameters
    vtail_S: Optional[float] = Field(None, description="Vertical tail area (S)")
    vtail_A: Optional[float] = Field(None, description="Vertical tail aspect ratio (A)")
    vtail_lambda: Optional[float] = Field(None, description="Vertical tail taper ratio (λ)")
    vtail_sweep_angle: Optional[float] = Field(None, description="Vertical tail sweep angle")
    
    mach_numbers: Optional[List[float]] = Field(None, description="List of Mach numbers for analysis")
    altitudes: Optional[List[float]] = Field(None, description="List of altitudes in feet")
    alpha_degrees: Optional[List[float]] = Field(None, description="List of angles of attack in degrees")
    weight: Optional[float] = Field(None, description="Aircraft weight in lbs")
    # High-level body params for internal calculation
    fuselage_length: Optional[float] = Field(None, description="Fuselage length in feet")
    max_diameter: Optional[float] = Field(None, description="Fuselage maximum diameter in feet")
    nose_cone_length_ratio: Optional[float] = Field(0.2, description="Nose cone length as a fraction of total length")
    tail_cone_length_ratio: Optional[float] = Field(0.2, description="Tail cone length as a fraction of total length")
    # Low-level body params for direct tool call
    x_coords: Optional[List[float]] = Field(None, description="List of longitudinal (X) station coordinates.")
    zu_coords: Optional[List[float]] = Field(None, description="List of upper surface (ZU) Z-coordinates at each station.")
    zl_coords: Optional[List[float]] = Field(None, description="List of lower surface (ZL) Z-coordinates at each station.")
    
    xcg: Optional[float] = Field(None, description="Center of gravity position (XCG) in feet")
    xw: Optional[float] = Field(None, description="Wing position (XW) in feet")
    xh: Optional[float] = Field(None, description="Horizontal tail position (XH) in feet")

PARAM_EXTRACTION_PROMPT = """Extract all DATCOM parameters from the user query below. 
Return ONLY a valid JSON object with the following fields (use null for missing values):
{{
  "wing_S": <number or null>,
  "wing_A": <number or null>,
  "wing_lambda": <number or null>,
  "wing_sweep_angle": <number or null>,
  "htail_S": <number or null>,
  "htail_A": <number or null>,
  "htail_lambda": <number or null>,
  "htail_sweep_angle": <number or null>,
  "vtail_S": <number or null>,
  "vtail_A": <number or null>,
  "vtail_lambda": <number or null>,
  "vtail_sweep_angle": <number or null>,
  "mach_numbers": [<numbers>] or null,
  "altitudes": [<numbers>] or null,
  "alpha_degrees": [<numbers>] or null,
  "weight": <number or null>,
  "fuselage_length": <number or null>,
  "max_diameter": <number or null>,
  "xcg": <number or null>,
  "xw": <number or null>,
  "xh": <number or null>
}}

IMPORTANT: 
- For angle of attack ranges like "-2到10度步進2度", extract as a list: [-2, 0, 2, 4, 6, 8, 10]
- Only extract values explicitly mentioned in the query
- Use null for any parameter not mentioned
- Return ONLY the JSON object, no explanations

User Query: {query}

JSON Output:"""

def _create_param_extractor(llm: ChatOpenAI) -> callable:
    """Creates a function to extract DATCOM parameters from a query."""
    prompt = ChatPromptTemplate.from_template(PARAM_EXTRACTION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    def _extract(query: str) -> DatcomParams:
        try:
            result = chain.invoke({"query": query})
            # Try to extract JSON from the response
            result = result.strip()
            
            # Find JSON object in response
            if '{' in result:
                start = result.index('{')
                end = result.rindex('}') + 1
                json_str = result[start:end]
                params_dict = json.loads(json_str)
                return DatcomParams(**params_dict)
            else:
                log(f"Warning: No JSON found in extraction result: {result}")
                return DatcomParams()
        except Exception as e:
            log(f"Warning: Failed to extract parameters: {e}")
            return DatcomParams()
    
    return _extract

# --- DATCOM Output Formatter ---

def _build_datcom_format(tool_responses: List[Dict[str, Any]], question: str) -> str:
    """Build DATCOM .dat format output from tool responses."""
    aircraft_name = "CUSTOM AIRCRAFT" # Simplified for now
    
    namelists = {}
    for tr in tool_responses:
        try:
            data = json.loads(tr['content']) if isinstance(tr['content'], str) else tr['content']
            if isinstance(data, dict) and 'error' not in data:
                namelists[tr['name']] = data
        except (json.JSONDecodeError, TypeError):
            pass

    lines = []
    lines.append(f"CASEID ----- {aircraft_name} -----")
    
    if 'generate_fltcon_matrix' in namelists:
        flt = namelists['generate_fltcon_matrix']
        mach_str = ', '.join(map(str, flt.get('MACH', [])))
        alpha_str = ', '.join(map(str, flt.get('ALSCHD', [])))
        alt_str = ', '.join(map(str, flt.get('ALT', [])))
        lines.append(f"$FLTCON NMACH={flt.get('NMACH', 1.0)},MACH(1)={mach_str},NALPHA={flt.get('NALPHA', 1.0)},ALSCHD(1)={alpha_str},")
        lines.append(f" NALT={flt.get('NALT', 1.0)},ALT(1)={alt_str},")
        lines.append(f" WT={flt.get('WT', 0.0)},LOOP={flt.get('LOOP', 1.0)}.$")

    if 'calculate_synthesis_positions' in namelists:
        syn = namelists['calculate_synthesis_positions']
        lines.append(f"$SYNTHS XCG={syn.get('XCG', 0.0)},ZCG={syn.get('ZCG', 0.0)},XW={syn.get('XW', 0.0)},ZW={syn.get('ZW', 0.0)},ALIW={syn.get('ALIW', 0.0)},XH={syn.get('XH', 0.0)},")
        lines.append(f" ZH={syn.get('ZH', 0.0)},ALIH={syn.get('ALIH', 0.0)},XV={syn.get('XV', 0.0)},ZV={syn.get('ZV', 0.0)}$")

    if 'convert_wing_to_datcom' in namelists:
        wing = namelists['convert_wing_to_datcom']
        lines.append(f"$OPTINS SREF={wing.get('SREF', 0.0)}$")

    if 'define_body_geometry' in namelists:
        body = namelists['define_body_geometry']
        x_vals = ', '.join(map(str, body.get('X', [])))
        zu_vals = ', '.join(map(str, body.get('ZU', [])))
        zl_vals = ', '.join(map(str, body.get('ZL', [])))
        lines.append(f"$BODY NX={body.get('NX', 0.0)},METHOD={body.get('METHOD', 1)},")
        lines.append(f" X(1)={x_vals},")
        lines.append(f" ZU(1)={zu_vals},")
        lines.append(f" ZL(1)={zl_vals}$")

    if 'convert_wing_to_datcom' in namelists:
        wing = namelists['convert_wing_to_datcom']
        lines.append(wing.get('airfoil', 'NACA-W-4-2412'))
        lines.append(f"$WGPLNF CHRDTP={wing.get('CHRDTP', 0.0)},SSPNOP={wing.get('SSPNOP', 0.0)},SSPNE={wing.get('SSPNE', 0.0)},SSPN={wing.get('SSPN', 0.0)},")
        lines.append(f" CHRDBP={wing.get('CHRDBP', 0.0)},CHRDR={wing.get('CHRDR', 0.0)},SAVSI={wing.get('SAVSI', 0.0)},SAVSO={wing.get('SAVSO', 0.0)},CHSTAT={wing.get('CHSTAT', 0.25)},")
        lines.append(f" TWISTA={wing.get('TWISTA', 0.0)},DHDADI={wing.get('DHDADI', 0.0)},DHDADO={wing.get('DHDADO', 0.0)},TYPE={wing.get('TYPE', 1.0)}.$")

    # Horizontal tail
    if 'convert_htail_to_datcom' in namelists:
        htail = namelists['convert_htail_to_datcom']
        lines.append(htail.get('airfoil', 'NACA-H-4-0012'))
        lines.append(f"$HTPLNF CHRDTP={htail.get('CHRDTP', 0.0)},SSPNE={htail.get('SSPNE', 0.0)},SSPN={htail.get('SSPN', 0.0)},")
        lines.append(f" CHRDR={htail.get('CHRDR', 0.0)},SAVSI={htail.get('SAVSI', 0.0)},CHSTAT={htail.get('CHSTAT', 0.0)},")
        lines.append(f" TWISTA={htail.get('TWISTA', 0.0)},DHDADI={htail.get('DHDADI', 0.0)},TYPE={htail.get('TYPE', 1.0)}.$")

    # Vertical tail
    if 'convert_vtail_to_datcom' in namelists:
        vtail = namelists['convert_vtail_to_datcom']
        lines.append(vtail.get('airfoil', 'NACA-V-4-0012'))
        lines.append(f"$VTPLNF CHRDTP={vtail.get('CHRDTP', 0.0)},SSPNE={vtail.get('SSPNE', 0.0)},SSPN={vtail.get('SSPN', 0.0)},")
        lines.append(f" CHRDR={vtail.get('CHRDR', 0.0)},SAVSI={vtail.get('SAVSI', 0.0)},CHSTAT={vtail.get('CHSTAT', 0.0)},TYPE={vtail.get('TYPE', 1.0)}.$")

    lines.extend(["DIM FT", "BUILD", "PLOT", "NEXT CASE"])
    return "\n".join(lines)

# --- DATCOM Sequence Node ---

def create_datcom_sequence_node(llm: ChatOpenAI) -> callable:
    """
    Creates a node that runs a fixed sequence of DATCOM tools.
    This is a non-agentic, reliable way to generate DATCOM files.
    """
    param_extractor = _create_param_extractor(llm)
    tools = {t.name: t for t in create_datcom_calculator_tools()}

    def datcom_sequence_node(state: GraphState) -> dict:
        log("--- RUNNING DATCOM FIXED SEQUENCE ---")
        question = state["question"]
        
        log("Extracting parameters from query...")
        params = param_extractor(question)
        log(f"Extracted parameters: {params}")

        # Auto-estimate tail parameters if wing is provided but tails are missing
        # Typical ratios for fighter aircraft:
        # - Horizontal tail area: 20-30% of wing area
        # - Vertical tail area: 15-20% of wing area
        if params.wing_S and not (params.htail_S and params.htail_A):
            log("⚠️  Horizontal tail parameters not provided. Estimating from wing geometry...")
            params.htail_S = params.wing_S * 0.25  # 25% of wing area
            params.htail_A = 3.5  # Typical aspect ratio for horizontal tail
            params.htail_lambda = 0.4  # Typical taper ratio
            params.htail_sweep_angle = max(0, params.wing_sweep_angle - 10)  # Slightly less sweep
            log(f"   Estimated: S={params.htail_S:.1f} ft², A={params.htail_A}, λ={params.htail_lambda}, sweep={params.htail_sweep_angle}°")
        
        if params.wing_S and not (params.vtail_S and params.vtail_A):
            log("⚠️  Vertical tail parameters not provided. Estimating from wing geometry...")
            params.vtail_S = params.wing_S * 0.18  # 18% of wing area
            params.vtail_A = 1.8  # Typical aspect ratio for vertical tail
            params.vtail_lambda = 0.5  # Typical taper ratio
            params.vtail_sweep_angle = max(0, params.wing_sweep_angle - 5)  # Similar sweep
            log(f"   Estimated: S={params.vtail_S:.1f} ft², A={params.vtail_A}, λ={params.vtail_lambda}, sweep={params.vtail_sweep_angle}°")

        tool_responses = []

        # Call tools in a fixed, reliable sequence
        if params.wing_S and params.wing_A and params.wing_lambda and params.wing_sweep_angle:
            log("Calling convert_wing_to_datcom")
            response = tools['convert_wing_to_datcom'].invoke({
                "S": params.wing_S,
                "A": params.wing_A,
                "lambda_": params.wing_lambda,
                "sweep_angle": params.wing_sweep_angle
            })
            tool_responses.append({"name": "convert_wing_to_datcom", "content": response})

        # Horizontal tail conversion
        if params.htail_S and params.htail_A and params.htail_lambda and params.htail_sweep_angle:
            log("Calling convert_tail_to_datcom for horizontal tail")
            response = tools['convert_tail_to_datcom'].invoke({
                "component": "horizontal_tail",
                "S": params.htail_S,
                "A": params.htail_A,
                "lambda_": params.htail_lambda,
                "sweep_angle": params.htail_sweep_angle,
                "is_vertical": False
            })
            tool_responses.append({"name": "convert_htail_to_datcom", "content": response})

        # Vertical tail conversion
        if params.vtail_S and params.vtail_A and params.vtail_lambda and params.vtail_sweep_angle:
            log("Calling convert_tail_to_datcom for vertical tail")
            response = tools['convert_tail_to_datcom'].invoke({
                "component": "vertical_tail",
                "S": params.vtail_S,
                "A": params.vtail_A,
                "lambda_": params.vtail_lambda,
                "sweep_angle": params.vtail_sweep_angle,
                "is_vertical": True
            })
            tool_responses.append({"name": "convert_vtail_to_datcom", "content": response})

        if params.mach_numbers and params.altitudes:
            log("Calling generate_fltcon_matrix")
            # Convert alpha_degrees list to alpha_range tuple if provided as list
            if params.alpha_degrees:
                # If we have a list, infer the range
                alphas = sorted(params.alpha_degrees)
                if len(alphas) > 1:
                    alpha_start = alphas[0]
                    alpha_end = alphas[-1]
                    # Try to infer step size
                    alpha_step = alphas[1] - alphas[0] if len(alphas) > 1 else 2.0
                    alpha_range = (alpha_start, alpha_end, alpha_step)
                else:
                    # Single value, use as both start and end with step=1
                    alpha_range = (alphas[0], alphas[0], 1.0)
            else:
                # Default range if not specified
                alpha_range = (-2.0, 10.0, 2.0)
            
            response = tools['generate_fltcon_matrix'].invoke({
                "mach_numbers": params.mach_numbers, 
                "altitudes": params.altitudes,
                "alpha_range": alpha_range, 
                "weight": params.weight or 0.0
            })
            tool_responses.append({"name": "generate_fltcon_matrix", "content": response})

        if params.xcg and params.xw and params.xh:
            log("Calling calculate_synthesis_positions")
            # User provided explicit positions, but tool needs fuselage_length
            # Use fuselage_length if available, otherwise estimate
            if params.fuselage_length:
                fuselage_len = params.fuselage_length
            else:
                # Estimate fuselage length from the furthest position + some margin
                fuselage_len = max(params.xcg or 0, params.xw or 0, params.xh or 0) * 1.15
            
            # Calculate percentages from user's explicit positions
            cg_percent = params.xcg / fuselage_len if fuselage_len > 0 else 0.35
            wing_percent = params.xw / fuselage_len if fuselage_len > 0 else 0.40
            htail_percent = params.xh / fuselage_len if fuselage_len > 0 else 0.90
            
            response = tools['calculate_synthesis_positions'].invoke({
                "fuselage_length": fuselage_len,
                "cg_position_percent": cg_percent,
                "wing_position_percent": wing_percent,
                "htail_position_percent": htail_percent
            })
            tool_responses.append({"name": "calculate_synthesis_positions", "content": response})

        # --- Body Geometry Logic ---
        if params.x_coords and params.zu_coords and params.zl_coords:
            # Case 1: User provided low-level coordinates directly
            log("Calling define_body_geometry with provided coordinates")
            response = tools['define_body_geometry'].invoke({
                "x_coords": params.x_coords, "zu_coords": params.zu_coords, "zl_coords": params.zl_coords
            })
            tool_responses.append({"name": "define_body_geometry", "content": response})
        elif params.fuselage_length and params.max_diameter:
            # Case 2: User provided high-level params, so we calculate coords internally
            log("Calculating body coordinates from high-level parameters")
            num_stations = 8
            nose_length = params.fuselage_length * params.nose_cone_length_ratio
            tail_length = params.fuselage_length * params.tail_cone_length_ratio
            max_radius = params.max_diameter / 2
            constant_section_end = params.fuselage_length - tail_length
            
            x_coords, zu_coords, zl_coords = [], [], []
            for i in range(num_stations):
                x = (params.fuselage_length / (num_stations - 1)) * i
                x_coords.append(round(x, 2))
                
                if x <= nose_length:
                    r = max_radius * math.sqrt(x / nose_length)
                elif x <= constant_section_end:
                    r = max_radius
                else:
                    r = max_radius * ((params.fuselage_length - x) / tail_length)
                
                zu_coords.append(round(r, 2))
                zl_coords.append(round(-r, 2)) # Assuming symmetric body

            response = tools['define_body_geometry'].invoke({
                "x_coords": x_coords, "zu_coords": zu_coords, "zl_coords": zl_coords
            })
            tool_responses.append({"name": "define_body_geometry", "content": response})

        log("Formatting final DATCOM file...")
        final_answer = _build_datcom_format(tool_responses, question)
        
        return {"generation": final_answer}

    return datcom_sequence_node
