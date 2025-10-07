"""
Node for executing a fixed sequence of DATCOM tool calls.
"""
import json
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
    mach_numbers: Optional[List[float]] = Field(None, description="List of Mach numbers for analysis")
    altitudes: Optional[List[float]] = Field(None, description="List of altitudes in feet")
    alpha_degrees: Optional[List[float]] = Field(None, description="List of angles of attack in degrees")
    weight: Optional[float] = Field(None, description="Aircraft weight in lbs")
    body_length: Optional[float] = Field(None, description="Fuselage length in feet")
    body_max_diameter: Optional[float] = Field(None, description="Fuselage maximum diameter in feet")
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
  "mach_numbers": [<numbers>] or null,
  "altitudes": [<numbers>] or null,
  "alpha_degrees": [<numbers>] or null,
  "weight": <number or null>,
  "body_length": <number or null>,
  "body_max_diameter": <number or null>,
  "xcg": <number or null>,
  "xw": <number or null>,
  "xh": <number or null>
}}

Do not make up values; only extract what is explicitly mentioned.

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

# --- DATCOM Output Formatter (moved from node.py) ---

def _build_datcom_format(tool_responses: List[Dict[str, Any]], question: str) -> str:
    """Build DATCOM .dat format output from tool responses."""
    aircraft_name = "CUSTOM AIRCRAFT" # Simplified for now
    
    namelists = {}
    for tr in tool_responses:
        try:
            # The tool content is already a dict/json string, so we parse it
            data = json.loads(tr['content']) if isinstance(tr['content'], str) else tr['content']
            if isinstance(data, dict) and 'error' not in data:
                namelists[tr['name']] = data
        except (json.JSONDecodeError, TypeError):
            pass

    lines = []
    lines.append(f"CASEID ----- {aircraft_name} -----")
    
    if 'generate_fltcon_matrix' in namelists:
        flt = namelists['generate_fltcon_matrix']
        mach_str = ','.join(map(str, flt.get('MACH', [])))
        alpha_str = ','.join(map(str, flt.get('ALSCHD', [])))
        alt_str = ','.join(map(str, flt.get('ALT', [])))
        lines.append(f"$FLTCON NMACH={flt.get('NMACH', 1.0)},MACH(1)={mach_str},NALPHA={flt.get('NALPHA', 1.0)},ALSCHD(1)={alpha_str},")
        lines.append(f" NALT={flt.get('NALT', 1.0)},ALT(1)={alt_str},")
        lines.append(f" WT={flt.get('WT', 0.0)},LOOP={flt.get('LOOP', 1.0)}.")

    if 'calculate_synthesis_positions' in namelists:
        syn = namelists['calculate_synthesis_positions']
        lines.append(f"$SYNTHS XCG={syn.get('XCG', 0.0)},ZCG={syn.get('ZCG', 0.0)},XW={syn.get('XW', 0.0)},ZW={syn.get('ZW', 0.0)},ALIW={syn.get('ALIW', 0.0)},XH={syn.get('XH', 0.0)},")
        lines.append(f" ZH={syn.get('ZH', 0.0)},ALIH={syn.get('ALIH', 0.0)},XV={syn.get('XV', 0.0)},ZV={syn.get('ZV', 0.0)}.")

    if 'convert_wing_to_datcom' in namelists:
        wing = namelists['convert_wing_to_datcom']
        lines.append(f"$OPTINS SREF={wing.get('SREF', 0.0)}.")

    if 'define_body_geometry' in namelists:
        body = namelists['define_body_geometry']
        x_vals = ','.join(map(str, body.get('X', [])))
        s_vals = ','.join(map(str, body.get('S', [])))
        lines.append(f"$BODY NX={body.get('NX', 0.0)},")
        lines.append(f" X(1)={x_vals},")
        lines.append(f" S(1)={s_vals}.")

    if 'convert_wing_to_datcom' in namelists:
        wing = namelists['convert_wing_to_datcom']
        lines.append(wing.get('airfoil', 'NACA-W-6-66-012'))
        lines.append(f"$WGPLNF CHRDTP={wing.get('CHRDTP', 0.0)},SSPNOP={wing.get('SSPNOP', 0.0)},SSPNE={wing.get('SSPNE', 0.0)},SSPN={wing.get('SSPN', 0.0)},")
        lines.append(f" CHRDBP={wing.get('CHRDBP', 0.0)},CHRDR={wing.get('CHRDR', 0.0)},SAVSI={wing.get('SAVSI', 0.0)},SAVSO={wing.get('SAVSO', 0.0)},CHSTAT={wing.get('CHSTAT', 0.25)},")
        lines.append(f" TWISTA={wing.get('TWISTA', 0.0)},DHDADI={wing.get('DHDADI', 0.0)},DHDADO={wing.get('DHDADO', 0.0)},TYPE={wing.get('TYPE', 1.0)}.")

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
        
        # 1. Extract parameters from the query
        log("Extracting parameters from query...")
        params = param_extractor(question)
        log(f"Extracted parameters: {params}")

        tool_responses = []

        # 2. Call tools in a fixed, reliable sequence
        if params.wing_S and params.wing_A and params.wing_lambda and params.wing_sweep_angle:
            log("Calling convert_wing_to_datcom")
            response = tools['convert_wing_to_datcom'].invoke({
                "S": params.wing_S, "A": params.wing_A, 
                "lambda_": params.wing_lambda, "sweep_angle": params.wing_sweep_angle
            })
            tool_responses.append({"name": "convert_wing_to_datcom", "content": response})

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
            # Use body_length if available, otherwise estimate
            if params.body_length:
                fuselage_len = params.body_length
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

        if params.body_length and params.body_max_diameter:
            log("Calling define_body_geometry")
            # Estimate nose and tail lengths if not provided
            # Typically: nose ~20%, tail ~20%, constant section ~60%
            nose_len = params.body_length * 0.2
            tail_len = params.body_length * 0.2
            
            response = tools['define_body_geometry'].invoke({
                "fuselage_length": params.body_length, 
                "max_diameter": params.body_max_diameter,
                "nose_length": nose_len,
                "tail_length": tail_len
            })
            tool_responses.append({"name": "define_body_geometry", "content": response})
        
        # 3. Format the final output
        log("Formatting final DATCOM file...")
        final_answer = _build_datcom_format(tool_responses, question)
        
        return {"generation": final_answer}

    return datcom_sequence_node
