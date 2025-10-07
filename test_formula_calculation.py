#!/usr/bin/env python3
"""測試 RAG 系統的公式檢索和計算能力"""

import subprocess
import re
from typing import Dict, List, Optional

class FormulaCalculationTest:
    """公式計算測試框架"""
    
    def __init__(self):
        self.test_cases = [
            {
                "name": "動壓計算",
                "question": "無人機在海平面飛行，空氣密度 ρ = 1.225 kg/m³，速度 V = 20 m/s。請使用動壓公式計算動壓 q 的數值。",
                "expected_keywords": ["q", "1/2", "ρ", "V", "動壓"],
                "expected_result": 245.0,
                "tolerance": 1.0,
                "unit": "Pa"
            },
            {
                "name": "升力計算",
                "question": "飛機機翼面積 S = 30 m²，動壓 q = 500 Pa，升力係數 CL = 1.2。請使用升力公式計算升力 L。",
                "expected_keywords": ["L", "CL", "q", "S", "升力"],
                "expected_result": 18000.0,
                "tolerance": 100.0,
                "unit": "N"
            },
            {
                "name": "阻力計算",
                "question": "飛機機翼面積 S = 30 m²，動壓 q = 500 Pa，阻力係數 CD = 0.05。請使用阻力公式計算阻力 D。",
                "expected_keywords": ["D", "CD", "q", "S", "阻力"],
                "expected_result": 750.0,
                "tolerance": 10.0,
                "unit": "N"
            }
        ]
    
    def run_query(self, question: str) -> str:
        """執行 RAG 查詢"""
        result = subprocess.run(
            ['./query.sh', question],
            capture_output=True,
            text=True,
            cwd='/home/c1147259/桌面/RAG'
        )
        
        output = result.stdout
        if "Final Answer:" in output:
            answer = output.split("Final Answer:")[1].strip()
            return answer
        return output
    
    def extract_number(self, text: str) -> Optional[float]:
        """從文本中提取數值結果（改進版）"""
        # 移除 LaTeX 格式
        text_clean = re.sub(r'\\text\{[^}]+\}', '', text)
        text_clean = re.sub(r'\\,', '', text_clean)
        
        patterns = [
            r'=\s*([\d,]+\.?\d*)\s*(?:Pa|N|m/s|cm/px|kg|m²|帕斯卡)',
            r'為\s*([\d,]+\.?\d*)\s*(?:Pa|N|帕斯卡|牛頓)',
            r'約為?\s*([\d,]+\.?\d*)',
            r'結果.*?([\d,]+\.?\d*)',
            r'\*\*([\d,]+\.?\d*)\s*(?:Pa|N|帕斯卡|牛頓)',
            r'([\d,]+\.?\d*)\s*\\?\s*(?:Pa|N|帕斯卡|牛頓)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_clean)
            if match:
                num_str = match.group(1).replace(',', '')
                try:
                    return float(num_str)
                except ValueError:
                    continue
        
        return None
    
    def check_formula_retrieval(self, answer: str, keywords: List[str]) -> bool:
        """檢查是否正確檢索公式"""
        found = sum(1 for kw in keywords if kw.lower() in answer.lower())
        return found >= len(keywords) * 0.5
    
    def validate_result(self, computed: float, expected: float, tolerance: float) -> bool:
        """驗證計算結果"""
        return abs(computed - expected) <= tolerance
    
    def run_test(self, test_case: Dict) -> Dict:
        """執行單個測試案例"""
        print(f"\n{'='*60}")
        print(f"測試: {test_case['name']}")
        print(f"{'='*60}")
        print(f"❓ 問題: {test_case['question']}\n")
        
        answer = self.run_query(test_case['question'])
        print(f"💬 LLM 回答:\n{answer}\n")
        
        # 檢查公式檢索
        has_formula = self.check_formula_retrieval(answer, test_case['expected_keywords'])
        print(f"{'✓' if has_formula else '✗'} 公式檢索: {'成功' if has_formula else '失敗'}")
        
        # 提取計算結果
        computed_value = self.extract_number(answer)
        if computed_value is None:
            print(f"✗ 數值提取: 失敗")
            return {
                "name": test_case['name'],
                "passed": False,
                "formula_retrieved": has_formula,
                "value_extracted": False,
                "calculation_correct": False
            }
        
        print(f"✓ 數值提取: {computed_value} {test_case['unit']}")
        
        # 驗證計算
        is_correct = self.validate_result(
            computed_value, 
            test_case['expected_result'], 
            test_case['tolerance']
        )
        
        expected = test_case['expected_result']
        tolerance = test_case['tolerance']
        print(f"📊 預期結果: {expected} ± {tolerance} {test_case['unit']}")
        print(f"{'✓' if is_correct else '✗'} 計算驗證: {'正確' if is_correct else '錯誤'}")
        
        return {
            "name": test_case['name'],
            "passed": has_formula and is_correct,
            "formula_retrieved": has_formula,
            "value_extracted": True,
            "calculation_correct": is_correct,
            "computed": computed_value,
            "expected": expected
        }
    
    def run_all_tests(self):
        """執行所有測試"""
        print("\n" + "="*60)
        print("🧪 RAG 系統公式計算能力測試")
        print("="*60)
        
        results = []
        for test_case in self.test_cases:
            result = self.run_test(test_case)
            results.append(result)
        
        # 統計結果
        print("\n" + "="*60)
        print("📈 測試總結")
        print("="*60)
        
        passed = sum(1 for r in results if r['passed'])
        total = len(results)
        
        for r in results:
            status = "✓ PASS" if r['passed'] else "✗ FAIL"
            details = []
            if not r.get('formula_retrieved', True):
                details.append("公式檢索失敗")
            if not r.get('value_extracted', True):
                details.append("數值提取失敗")
            if not r.get('calculation_correct', True):
                details.append("計算錯誤")
            
            detail_str = f" ({', '.join(details)})" if details else ""
            print(f"{status}: {r['name']}{detail_str}")
        
        print(f"\n🎯 通過率: {passed}/{total} ({passed/total*100:.1f}%)")
        
        # 能力分析
        print(f"\n📊 能力分析:")
        formula_ok = sum(1 for r in results if r.get('formula_retrieved', False))
        extract_ok = sum(1 for r in results if r.get('value_extracted', False))
        calc_ok = sum(1 for r in results if r.get('calculation_correct', False))
        
        print(f"   - 公式檢索能力: {formula_ok}/{total} ({formula_ok/total*100:.0f}%)")
        print(f"   - 數值提取能力: {extract_ok}/{total} ({extract_ok/total*100:.0f}%)")
        print(f"   - 計算準確度: {calc_ok}/{total} ({calc_ok/total*100:.0f}%)")
        
        return results

if __name__ == "__main__":
    tester = FormulaCalculationTest()
    tester.run_all_tests()
