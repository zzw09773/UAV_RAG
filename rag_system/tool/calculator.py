"""Python calculation tool for mathematical operations and parameter derivation"""
from typing import Callable
from langchain.tools import tool
import math
from ..common import log


def create_calculator_tool() -> Callable:
    """Create Python calculator tool
    
    Returns:
        Calculator tool function that can execute mathematical operations and parameter derivation
    """
    @tool
    def python_calculator(expression: str) -> str:
        """Execute mathematical calculations or parameter derivations.
        
        This tool can perform mathematical operations, geometric calculations, etc. Suitable for:
        - Basic math operations (addition, subtraction, multiplication, division, exponentiation, square root)
        - Geometric parameter calculations (wingspan, mean chord, taper ratio conversion, etc.)
        - Unit conversions
        
        Args:
            expression: Python mathematical expression or calculation script
                       Examples: "sqrt(530 * 2.8)" to calculate wingspan
                                "530 / 38.5" to calculate mean chord
        
        Returns:
            Calculation result or error message (in Traditional Chinese)
        
        Examples:
            - Calculate wingspan: "math.sqrt(530 * 2.8)"
            - Calculate mean chord: "530 / math.sqrt(530 * 2.8)"
            - Derive root chord: "(2 * 530) / (38.5 * (1 + 0.3))"
        """
        log(f"Calculator executing: {expression}")
        
        try:
            # Safe mathematical namespace
            safe_namespace = {
                'math': math,
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'pi': math.pi,
                'abs': abs,
                'round': round,
                'pow': pow,
            }
            
            # Execute calculation
            result = eval(expression, {"__builtins__": {}}, safe_namespace)
            
            log(f"Calculator result: {result}")
            return f"計算結果: {result}"
            
        except Exception as e:
            error_msg = f"計算錯誤: {str(e)}"
            log(f"ERROR: {error_msg}")
            return error_msg
    
    return python_calculator
