#!/usr/bin/env python3
"""測試 DATCOM 計算器工具的完整功能

此腳本測試所有 DATCOM 參數轉換工具，確保它們能正確計算並生成有效的參數。
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.tool.datcom_calculator import (
    convert_wing_to_datcom,
    convert_tail_to_datcom,
    calculate_synthesis_positions,
    define_body_geometry,
    generate_fltcon_matrix,
    validate_datcom_parameters
)


def print_section(title: str):
    """打印測試區塊標題"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(tool_name: str, result: dict):
    """打印工具結果"""
    print(f"\n{tool_name} 結果:")
    print("-" * 80)
    
    # 分離顯示: 主要參數 vs 推導參數
    main_params = {}
    derived_params = {}
    
    for k, v in result.items():
        if k.startswith('_'):
            derived_params[k] = v
        else:
            main_params[k] = v
    
    # 顯示主要參數 (用於 for005.dat)
    print("📋 DATCOM 參數 (for005.dat):")
    for k, v in main_params.items():
        if isinstance(v, (int, float)):
            print(f"  {k:12} = {v}")
        else:
            print(f"  {k:12} = {v}")
    
    # 顯示推導參數 (驗證用)
    if derived_params:
        print("\n🔍 推導參數 (驗證用):")
        for k, v in derived_params.items():
            if k == '_formulas':
                print(f"  {k}:")
                for fk, fv in v.items():
                    print(f"    {fk}: {fv}")
            elif isinstance(v, dict):
                print(f"  {k}:")
                for dk, dv in v.items():
                    print(f"    {dk}: {dv}")
            else:
                print(f"  {k:20} = {v}")


def test_f4_phantom():
    """測試 F-4 Phantom II 完整參數計算"""
    
    print_section("F-4 Phantom II 戰鬥機 - 完整 DATCOM 參數生成測試")
    
    # ========================================================================
    # 1. 機翼參數轉換
    # ========================================================================
    print_section("1. 機翼參數轉換 ($WGPLNF)")
    print("輸入參數: S=530 ft², A=2.8, λ=0.3, Sweep=45°, Dihedral=-3°")
    
    wing_result = convert_wing_to_datcom.invoke({
        "S": 530,
        "A": 2.8,
        "lambda_": 0.3,
        "sweep_angle": 45,
        "dihedral": -3.0,
        "twist": -2.0,
        "airfoil": "0006-64"  # F-4 使用薄翼型
    })
    print_result("convert_wing_to_datcom", wing_result)
    
    # ========================================================================
    # 2. 水平尾翼參數
    # ========================================================================
    print_section("2. 水平尾翼參數轉換 ($HTPLNF)")
    print("輸入參數: S=100 ft², A=3.0, λ=0.4, Sweep=35°")
    
    htail_result = convert_tail_to_datcom.invoke({
        "component": "horizontal_tail",
        "S": 100,
        "A": 3.0,
        "lambda_": 0.4,
        "sweep_angle": 35
    })
    print_result("convert_tail_to_datcom (H-tail)", htail_result)
    
    # ========================================================================
    # 3. 垂直尾翼參數
    # ========================================================================
    print_section("3. 垂直尾翼參數轉換 ($VTPLNF)")
    print("輸入參數: S=80 ft², A=1.5, λ=0.3, Sweep=45°")
    
    vtail_result = convert_tail_to_datcom.invoke({
        "component": "vertical_tail",
        "S": 80,
        "A": 1.5,
        "lambda_": 0.3,
        "sweep_angle": 45,
        "is_vertical": True
    })
    print_result("convert_tail_to_datcom (V-tail)", vtail_result)
    
    # ========================================================================
    # 4. 組件位置計算
    # ========================================================================
    print_section("4. 組件位置計算 ($SYNTHS)")
    print("輸入參數: 機身長度=58.3 ft, 機翼位置=42%, H-tail=90%, V-tail=65%, CG=35%")
    
    synths_result = calculate_synthesis_positions.invoke({
        "fuselage_length": 58.3,
        "wing_position_percent": 0.42,
        "htail_position_percent": 0.90,
        "vtail_position_percent": 0.65,
        "cg_position_percent": 0.35,
        "wing_z": 0.5,
        "htail_z": 2.0
    })
    print_result("calculate_synthesis_positions", synths_result)
    
    # ========================================================================
    # 5. 機身幾何定義
    # ========================================================================
    print_section("5. 機身幾何定義 ($BODY)")
    print("輸入參數: 長度=58.3 ft, 最大直徑=3.0 ft, 機鼻=8 ft, 機尾=10 ft")
    
    body_result = define_body_geometry.invoke({
        "fuselage_length": 58.3,
        "max_diameter": 3.0,
        "nose_length": 8.0,
        "tail_length": 10.0,
        "num_stations": 10.0
    })
    print_result("define_body_geometry", body_result)
    
    # ========================================================================
    # 6. 飛行條件矩陣
    # ========================================================================
    print_section("6. 飛行條件矩陣 ($FLTCON)")
    print("輸入參數: Mach=[0.6,0.8,0.95], Alt=[10k,20k,30k], α=[-4°,14°,2°], W=38000 lbs")
    
    fltcon_result = generate_fltcon_matrix.invoke({
        "mach_numbers": [0.6, 0.8, 0.95],
        "altitudes": [10000, 20000, 30000],
        "alpha_range": (-4, 14, 2),
        "weight": 38000,
        "loop_mode": 2.0
    })
    print_result("generate_fltcon_matrix", fltcon_result)
    
    # ========================================================================
    # 7. 參數驗證
    # ========================================================================
    print_section("7. 參數驗證")
    
    validation_result = validate_datcom_parameters.invoke({
        "params": {
            "CHRDR": wing_result['CHRDR'],
            "CHRDTP": wing_result['CHRDTP'],
            "SSPN": wing_result['SSPN'],
            "SSPNE": wing_result['SSPNE'],
            "SAVSI": wing_result['SAVSI'],
            "DHDADI": wing_result['DHDADI']
        }
    })
    print_result("validate_datcom_parameters", validation_result)
    
    # ========================================================================
    # 8. 總結
    # ========================================================================
    print_section("測試總結")
    print(f"""
✅ 所有工具測試完成!

生成的參數可用於構建完整的 F-4 Phantom II for005.dat 檔案:

CASEID F-4 PHANTOM II
$FLTCON
  NMACH={fltcon_result['NMACH']}, MACH(1)={','.join(map(str, fltcon_result['MACH']))},
  NALT={fltcon_result['NALT']}, ALT(1)={','.join(map(str, fltcon_result['ALT']))},
  NALPHA={fltcon_result['NALPHA']},
  ALSCHD(1)={','.join(map(str, fltcon_result['ALSCHD']))},
  WT={fltcon_result['WT']}, LOOP={fltcon_result['LOOP']}
$
$SYNTHS
  XCG={synths_result['XCG']}, ZCG={synths_result['ZCG']},
  XW={synths_result['XW']}, ZW={synths_result['ZW']}, ALIW={synths_result['ALIW']},
  XH={synths_result['XH']}, ZH={synths_result['ZH']}, ALIH={synths_result['ALIH']},
  XV={synths_result['XV']}, ZV={synths_result['ZV']}
$
$WGPLNF
  CHRDR={wing_result['CHRDR']}, CHRDTP={wing_result['CHRDTP']},
  SSPN={wing_result['SSPN']}, SSPNE={wing_result['SSPNE']},
  SAVSI={wing_result['SAVSI']},
  DHDADI={wing_result['DHDADI']}, TWISTA={wing_result['TWISTA']},
  CHSTAT={wing_result['CHSTAT']}, TYPE={wing_result['TYPE']}
$
{wing_result['airfoil']}
...

分析點數: {fltcon_result['_analysis_points']}
驗證狀態: {validation_result['status']}
""")


def test_mig17():
    """測試 MiG-17 參數計算 (驗證與文檔範例的一致性)"""
    
    print_section("MiG-17 - 驗證與文檔範例的一致性")
    
    # 從文檔中的 MiG-17 已知參數反推
    # CHRDR=14.0, CHRDTP=7.02, SSPN=15.71
    # 計算應該的 S, A, λ
    
    print("已知 DATCOM 參數: CHRDR=14.0, CHRDTP=7.02, SSPN=15.71")
    print("計算標準參數...")
    
    CHRDR = 14.0
    CHRDTP = 7.02
    SSPN = 15.71
    
    lambda_ = CHRDTP / CHRDR
    b = SSPN * 2
    S = (b * (1 + lambda_) * CHRDR) / 2
    A = (b ** 2) / S
    
    print(f"  λ = {lambda_:.3f}")
    print(f"  b = {b:.2f} ft")
    print(f"  S = {S:.2f} ft²")
    print(f"  A = {A:.2f}")
    
    print("\n使用計算器工具重新生成...")
    result = convert_wing_to_datcom.invoke({
        "S": S,
        "A": A,
        "lambda_": lambda_,
        "sweep_angle": 45,
        "dihedral": -3.0,
        "airfoil": "66012"
    })
    
    print_result("convert_wing_to_datcom (MiG-17)", result)
    
    print("\n驗證:")
    print(f"  CHRDR 誤差: {abs(result['CHRDR'] - CHRDR):.4f} ft")
    print(f"  CHRDTP 誤差: {abs(result['CHRDTP'] - CHRDTP):.4f} ft")
    print(f"  SSPN 誤差: {abs(result['SSPN'] - SSPN):.4f} ft")
    
    if (abs(result['CHRDR'] - CHRDR) < 0.01 and 
        abs(result['CHRDTP'] - CHRDTP) < 0.01 and 
        abs(result['SSPN'] - SSPN) < 0.01):
        print("\n✅ 與文檔範例一致性驗證通過!")
    else:
        print("\n⚠️ 與文檔範例存在差異，請檢查公式")


def test_edge_cases():
    """測試邊界情況與錯誤處理"""
    
    print_section("邊界情況與錯誤處理測試")
    
    # 測試 1: 無效的尖削比
    print("\n測試 1: λ > 1.0 (應該報錯)")
    result1 = convert_wing_to_datcom.invoke({
        "S": 500,
        "A": 3.0,
        "lambda_": 1.5,  # 錯誤: 尖削比不能 > 1
        "sweep_angle": 30
    })
    print(f"  結果: {result1}")
    
    # 測試 2: 負面積
    print("\n測試 2: S < 0 (應該報錯)")
    result2 = convert_wing_to_datcom.invoke({
        "S": -100,
        "A": 3.0,
        "lambda_": 0.5,
        "sweep_angle": 30
    })
    print(f"  結果: {result2}")
    
    # 測試 3: 過多的攻角點
    print("\n測試 3: 超過 20 個攻角點 (應該報錯)")
    result3 = generate_fltcon_matrix.invoke({
        "mach_numbers": [0.6],
        "altitudes": [10000],
        "alpha_range": (-10, 30, 1),  # 41 個點
        "weight": 20000
    })
    print(f"  結果: {result3}")
    
    # 測試 4: 參數驗證 - CHRDTP > CHRDR
    print("\n測試 4: 翼尖弦長 > 翼根弦長 (應該警告)")
    result4 = validate_datcom_parameters.invoke({
        "params": {
            "CHRDR": 10.0,
            "CHRDTP": 12.0  # 錯誤: 尖削翼不應該這樣
        }
    })
    print(f"  結果: {result4}")


if __name__ == "__main__":
    # 執行所有測試
    test_f4_phantom()
    test_mig17()
    test_edge_cases()
    
    print("\n" + "=" * 80)
    print("  所有測試完成!")
    print("=" * 80)
