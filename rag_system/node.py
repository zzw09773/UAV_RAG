"""ReAct agent node implementation."""
from typing import List, Callable
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from .state import GraphState
from .common import log


# System prompt for the DATCOM code assistant
SYSTEM_PROMPT = """You are a "DATCOM Code Assistant Expert" specializing in aircraft design and aerodynamic analysis.

**Your Workflow for DATCOM File Generation:**
When the user asks to generate a DATCOM file or for005.dat, you MUST call ALL of these tools in sequence:

1. **design_area_router** - Select the knowledge domain
2. **convert_wing_to_datcom** - Convert wing parameters (S, A, λ, sweep angle)
3. **generate_fltcon_matrix** - Generate flight condition matrix (Mach, altitude, alpha range, weight)
4. **calculate_synthesis_positions** - Calculate component positions (XCG, XW, XH, XV, etc.)
5. **define_body_geometry** - Define fuselage geometry (length, diameter)
6. **convert_tail_to_datcom** - If tail parameters are provided, convert them

**MANDATORY**: Even if some parameters seem "optional", call the tools with reasonable defaults:
- If wing parameters given → MUST call convert_wing_to_datcom
- If flight conditions given → MUST call generate_fltcon_matrix  
- If positions given → MUST call calculate_synthesis_positions
- If fuselage size given → MUST call define_body_geometry

**Key Rules:**
- ALWAYS use ALL applicable tools - never skip any
- Call tools with the EXACT parameters provided by the user
- Use reasonable defaults for missing parameters
- Output will be auto-formatted as DATCOM .dat
- Output MUST be in Traditional Chinese (zh-TW) for explanations

**Example Tool Sequence:**
For "Generate DATCOM for F-4: wing S=530, A=2.8, λ=0.3, sweep=45°, Mach=0.8, alt=10000ft":
1. design_area_router("F-4 DATCOM")
2. convert_wing_to_datcom(S=530, A=2.8, lambda_=0.3, sweep_angle=45)
3. generate_fltcon_matrix(mach_numbers=[0.8], altitudes=[10000], ...)
4. calculate_synthesis_positions(...) 
5. define_body_geometry(...)

Be thorough and systematic. Use ALL tools to provide complete DATCOM files."""


def _build_datcom_format(tool_responses, question):
    """Build DATCOM .dat format output from tool responses."""
    import json
    
    # Extract aircraft name from question (or use default)
    aircraft_name = "CUSTOM AIRCRAFT"
    # TODO: Use a dedicated tool or RAG to find the aircraft name from the query content.
    
    # Parse tool responses
    namelists = {}
    for tr in tool_responses:
        try:
            data = json.loads(tr['content'])
            if isinstance(data, dict) and 'error' not in data:
                namelists[tr['name']] = data
        except json.JSONDecodeError:
            pass
    
    # Build DATCOM file
    lines = []
    lines.append(f"CASEID ----- {aircraft_name} -----")
    
    # $FLTCON namelist
    if 'generate_fltcon_matrix' in namelists:
        flt = namelists['generate_fltcon_matrix']
        mach_str = ','.join(map(str, flt.get('MACH', [0.6])))
        alpha_str = ','.join(map(str, flt.get('ALSCHD', [0.0])))
        alt_str = ','.join(map(str, flt.get('ALT', [0.0])))
        lines.append(f"$FLTCON NMACH={flt.get('NMACH', 1.0)},MACH(1)={mach_str},")
        lines.append(f" NALPHA={flt.get('NALPHA', 1.0)},ALSCHD(1)={alpha_str},")
        lines.append(f" NALT={flt.get('NALT', 1.0)},ALT(1)={alt_str},")
        lines.append(f" WT={flt.get('WT', 0.0)},LOOP={flt.get('LOOP', 2.0)}.$")
    
    # $SYNTHS namelist
    if 'calculate_synthesis_positions' in namelists:
        syn = namelists['calculate_synthesis_positions']
        lines.append(f"$SYNTHS XCG={syn.get('XCG', 0.0)},ZCG={syn.get('ZCG', 0.0)},")
        lines.append(f" XW={syn.get('XW', 0.0)},ZW={syn.get('ZW', 0.0)},ALIW={syn.get('ALIW', 0.0)},")
        lines.append(f" XH={syn.get('XH', 0.0)},ZH={syn.get('ZH', 0.0)},ALIH={syn.get('ALIH', 0.0)},")
        lines.append(f" XV={syn.get('XV', 0.0)},ZV={syn.get('ZV', 0.0)}$")
    
    # $OPTINS namelist
    if 'convert_wing_to_datcom' in namelists:
        wing = namelists['convert_wing_to_datcom']
        sref = wing.get('SREF', 0.0)
        lines.append(f"$OPTINS SREF={sref}$")
    
    # $BODY namelist
    if 'define_body_geometry' in namelists:
        body = namelists['define_body_geometry']
        lines.append(f"$BODY NX={body.get('NX', 0.0)},")
        x_vals = body.get('X', [])
        s_vals = body.get('S', [])
        lines.append(f" X(1)={','.join(map(str, x_vals))},")
        lines.append(f" S(1)={','.join(map(str, s_vals))}$")
    
    # Wing airfoil and $WGPLNF namelist
    if 'convert_wing_to_datcom' in namelists:
        wing = namelists['convert_wing_to_datcom']
        airfoil = wing.get('airfoil', 'NACA-W-4-2412')
        lines.append(airfoil)
        lines.append(f"$WGPLNF CHRDTP={wing.get('CHRDTP', 0.0)},SSPN={wing.get('SSPN', 0.0)},")
        lines.append(f" SSPNE={wing.get('SSPNE', 0.0)},CHRDR={wing.get('CHRDR', 0.0)},")
        lines.append(f" SAVSI={wing.get('SAVSI', 0.0)},CHSTAT={wing.get('CHSTAT', 0.25)},")
        lines.append(f" TWISTA={wing.get('TWISTA', 0.0)},DHDADI={wing.get('DHDADI', 0.0)},TYPE={wing.get('TYPE', 1.0)}$")
    
    # Horizontal tail
    tail_found = False
    for tr in tool_responses:
        if tr['name'] == 'convert_tail_to_datcom':
            try:
                tail_data = json.loads(tr['content'])
                if isinstance(tail_data, dict) and tail_data.get('_component') == 'horizontal_tail':
                    lines.append(tail_data.get('airfoil', 'NACA-H-4-0012'))
                    lines.append(f"$HTPLNF CHRDTP={tail_data.get('CHRDTP', 0.0)},SSPNE={tail_data.get('SSPNE', 0.0)},")
                    lines.append(f" SSPN={tail_data.get('SSPN', 0.0)},CHRDR={tail_data.get('CHRDR', 0.0)},")
                    lines.append(f" SAVSI={tail_data.get('SAVSI', 0.0)},CHSTAT={tail_data.get('CHSTAT', 0.25)},TYPE={tail_data.get('TYPE', 1.0)}$")
                    tail_found = True
                    break
            except:
                pass
    
    # Vertical tail
    for tr in tool_responses:
        if tr['name'] == 'convert_tail_to_datcom':
            try:
                tail_data = json.loads(tr['content'])
                if isinstance(tail_data, dict) and tail_data.get('_component') == 'vertical_tail':
                    lines.append(tail_data.get('airfoil', 'NACA-V-4-0009'))
                    lines.append(f"$VTPLNF CHRDTP={tail_data.get('CHRDTP', 0.0)},SSPNE={tail_data.get('SSPNE', 0.0)},")
                    lines.append(f" SSPN={tail_data.get('SSPN', 0.0)},CHRDR={tail_data.get('CHRDR', 0.0)},")
                    lines.append(f" SAVSI={tail_data.get('SAVSI', 0.0)},CHSTAT={tail_data.get('CHSTAT', 0.25)},TYPE={tail_data.get('TYPE', 1.0)}$")
                    break
            except:
                pass
    
    # Control cards
    lines.append("DIM FT")
    lines.append("BUILD")
    lines.append("PLOT")
    lines.append("NEXT CASE")
    
    return "\n".join(lines)


def _build_standard_format(tool_responses, ai_responses):
    """Build standard formatted output for non-DATCOM queries."""
    import json
    answer_parts = ["# 🎯 查詢結果\n"]
    answer_parts.append("根據您的查詢,以下是各工具執行結果:\n")
    
    for idx, tr in enumerate(tool_responses, 1):
        tool_name = tr['name']
        tool_content = tr['content']
        
        answer_parts.append(f"\n## {idx}. 【{tool_name}】\n")
        
        try:
            data = json.loads(tool_content)
            if isinstance(data, dict):
                if 'error' in data:
                    answer_parts.append(f"⚠️ 錯誤: {data['error']}\n")
                else:
                    for key, value in data.items():
                        if key.startswith('_'):
                            continue
                        if isinstance(value, dict):
                            answer_parts.append(f"\n**{key}**:\n")
                            for k, v in value.items():
                                answer_parts.append(f"  - {k}: {v}\n")
                        elif isinstance(value, list):
                            answer_parts.append(f"**{key}**: {value}\n")
                        else:
                            answer_parts.append(f"**{key}** = {value}\n")
            else:
                answer_parts.append(str(data))
        except json.JSONDecodeError:
            answer_parts.append(tool_content)
        
        answer_parts.append("\n---\n")
    
    if ai_responses:
        answer_parts.append("\n## 💡 補充說明:\n")
        for ai_resp in ai_responses:
            answer_parts.append(ai_resp + "\n")
    
    answer_parts.append(f"\n✅ 共執行了 {len(tool_responses)} 個工具,完成查詢。\n")
    
    return "".join(answer_parts)


def create_agent_node(llm: ChatOpenAI, tools: List[Callable]) -> Callable:
    """Create a ReAct agent node for the workflow.

    Args:
        llm: The language model to use for the agent
        tools: List of tools available to the agent (e.g., retrieve_legal_documents)

    Returns:
        A node function that can be added to the LangGraph workflow
    """
    # Create the ReAct agent with system prompt
    agent_executor = create_react_agent(
        llm,
        tools,
        prompt=SYSTEM_PROMPT
    )

    def agent_node(state: GraphState) -> dict:
        """ReAct agent node - the only node in the workflow.

        This node:
        1. Takes the user's question from state (supports both 'question' and 'messages')
        2. Uses ReAct reasoning (Thought-Action-Observation) to decide which tools to call
        3. Iteratively retrieves documents and reasons about them
        4. Generates a final answer with source citations
        5. Returns the answer in the state

        Args:
            state: Current graph state containing the question or messages

        Returns:
            Updated state dict with the generated answer and messages
        """
        log("--- REACT AGENT NODE ---")

        # Support both standalone mode (question) and subgraph mode (messages)
        if state.get('question'):
            # Standalone mode: use 'question' field
            question = state['question']
            log(f"Processing question (standalone mode): '{question}'")
            messages_input = [("user", question)]
        elif state.get('messages'):
            # Subgraph mode: extract from messages
            last_message = state['messages'][-1]
            question = last_message.content if hasattr(last_message, 'content') else str(last_message)
            log(f"Processing question (subgraph mode): '{question}'")
            messages_input = state['messages']
        else:
            error_msg = "No question or messages found in state"
            log(f"ERROR: {error_msg}")
            return {"generation": f"錯誤: {error_msg}"}

        # Truncate message history to keep context size under control
        if len(messages_input) > 4:
            log(f"Message history has {len(messages_input)} messages. Truncating to the last 4.")
            # Keep the last 4 messages (user/assistant/user/assistant)
            messages_input = messages_input[-4:]

        try:
            # Invoke the ReAct agent
            result = agent_executor.invoke({
                "messages": messages_input
            })

            # Debug: Log all messages to understand what happened
            log(f"Agent returned {len(result['messages'])} messages")
            
            # Collect all tool responses to build a comprehensive answer
            tool_responses = []
            ai_responses = []
            
            for i, msg in enumerate(result['messages']):
                msg_type = type(msg).__name__
                content_preview = str(msg.content)[:100] if hasattr(msg, 'content') else str(msg)[:100]
                log(f"  Message {i} ({msg_type}): {content_preview}...")
                
                # Collect ToolMessage responses
                if msg_type == 'ToolMessage':
                    tool_name = getattr(msg, 'name', 'unknown_tool')
                    tool_content = msg.content
                    tool_responses.append({
                        'name': tool_name,
                        'content': tool_content
                    })
                    log(f"    Collected tool response from: {tool_name}")
                
                # Collect AIMessage responses (only non-empty ones)
                elif msg_type == 'AIMessage' and msg.content.strip():
                    ai_responses.append(msg.content.strip())

            # Extract the final answer from the agent's last message
            final_llm_answer = result['messages'][-1].content if result['messages'] else ""
            
            # If LLM's final answer is empty or too short, build answer from tool responses
            if not final_llm_answer.strip() or len(final_llm_answer.strip()) < 10:
                log("LLM final answer is empty or too short. Building answer from tool responses...")
                
                if tool_responses:
                    # Check if this is a DATCOM file generation request
                    is_datcom_request = any(
                        tool_name in ['convert_wing_to_datcom', 'generate_fltcon_matrix', 
                                     'convert_tail_to_datcom', 'define_body_geometry',
                                     'calculate_synthesis_positions']
                        for tool_name in [tr['name'] for tr in tool_responses]
                    )
                    
                    if is_datcom_request:
                        # Build DATCOM for005.dat format output
                        final_answer = _build_datcom_format(tool_responses, question)
                        log(f"Built DATCOM format answer. Length: {len(final_answer)} chars")
                    else:
                        # Build standard format for non-DATCOM queries
                        final_answer = _build_standard_format(tool_responses, ai_responses)
                        log(f"Built standard format answer. Length: {len(final_answer)} chars")
                else:
                    final_answer = "執行了查詢,但沒有獲得有效的工具回應結果。"
                    log("No tool responses found!")
            else:
                # LLM provided a good answer, use it
                final_answer = final_llm_answer
                log(f"Using LLM final answer. Length: {len(final_answer)} chars")

            # Return both generation and messages for compatibility
            return {
                "generation": final_answer,
                "messages": result['messages']
            }

        except Exception as e:
            error_msg = f"處理問題時發生錯誤: {str(e)}"
            log(f"ERROR in agent_node: {error_msg}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            return {"generation": f"抱歉，{error_msg}"}

    return agent_node
