"""Python 計算工具，用於數學運算和參數推算"""
from typing import Callable
from langchain.tools import tool
import math
from ..common import log


def create_calculator_tool() -> Callable:
    """創建 Python 計算工具
    
    Returns:
        計算工具函數，可執行數學運算和參數推算
    """
    @tool
    def python_calculator(expression: str) -> str:
        """執行數學計算或參數推算。
        
        此工具可以執行數學運算、幾何計算等。適用於：
        - 基本數學運算（加減乘除、指數、平方根）
        - 幾何參數計算（翼展、平均弦長、錐度比換算等）
        - 單位轉換
        
        Args:
            expression: Python 數學表達式或計算腳本
                       例如: "sqrt(530 * 2.8)" 計算翼展
                            "530 / 38.5" 計算平均弦長
        
        Returns:
            計算結果或錯誤訊息
        
        Examples:
            - 計算翼展: "math.sqrt(530 * 2.8)"
            - 計算平均弦長: "530 / math.sqrt(530 * 2.8)"
            - 推算翼根弦長: "(2 * 530) / (38.5 * (1 + 0.3))"
        """
        log(f"Calculator executing: {expression}")
        
        try:
            # 安全的數學命名空間
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
            
            # 執行計算
            result = eval(expression, {"__builtins__": {}}, safe_namespace)
            
            log(f"Calculator result: {result}")
            return f"計算結果: {result}"
            
        except Exception as e:
            error_msg = f"計算錯誤: {str(e)}"
            log(f"ERROR: {error_msg}")
            return error_msg
    
    return python_calculator
