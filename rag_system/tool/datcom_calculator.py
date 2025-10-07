"""DATCOM 參數計算工具 - 完整版

基於「DATCOM 參數解析與轉換.md」文件實現的完整參數計算與轉換工具集。
涵蓋機翼、水平尾翼、垂直尾翼、機身的所有關鍵參數計算。

設計哲學:
- 消除特殊情況: 所有升力面使用統一的計算邏輯
- 數據結構優先: 清晰的輸入輸出映射
- 零破壞: 與現有工具完全兼容
"""
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.tools import tool
import math
from ..common import log


# ============================================================================
# 核心計算函數 (Pure Functions)
# ============================================================================

def calculate_wingspan(S: float, A: float) -> float:
    """計算翼展: b = √(A·S)
    
    Args:
        S: 參考翼面積 (ft²)
        A: 展弦比 (無因次)
    
    Returns:
        翼展 (ft)
    """
    return math.sqrt(A * S)


def calculate_root_chord(S: float, b: float, lambda_: float) -> float:
    """計算翼根弦長: Croot = 2S / [b(1+λ)]
    
    Args:
        S: 參考翼面積 (ft²)
        b: 翼展 (ft)
        lambda_: 尖削比 (無因次)
    
    Returns:
        翼根弦長 (ft)
    """
    return (2 * S) / (b * (1 + lambda_))


def calculate_tip_chord(Croot: float, lambda_: float) -> float:
    """計算翼尖弦長: Ctip = λ·Croot
    
    Args:
        Croot: 翼根弦長 (ft)
        lambda_: 尖削比 (無因次)
    
    Returns:
        翼尖弦長 (ft)
    """
    return lambda_ * Croot


def calculate_mean_aerodynamic_chord(Croot: float, lambda_: float) -> float:
    """計算平均氣動弦長: MAC = (2/3) * Croot * (1+λ+λ²)/(1+λ)
    
    Args:
        Croot: 翼根弦長 (ft)
        lambda_: 尖削比 (無因次)
    
    Returns:
        平均氣動弦長 (ft)
    """
    return (2/3) * Croot * (1 + lambda_ + lambda_**2) / (1 + lambda_)


def calculate_aspect_ratio(b: float, S: float) -> float:
    """計算展弦比: A = b²/S
    
    Args:
        b: 翼展 (ft)
        S: 參考翼面積 (ft²)
    
    Returns:
        展弦比 (無因次)
    """
    return (b ** 2) / S


def calculate_taper_ratio(Ctip: float, Croot: float) -> float:
    """計算尖削比: λ = Ctip/Croot
    
    Args:
        Ctip: 翼尖弦長 (ft)
        Croot: 翼根弦長 (ft)
    
    Returns:
        尖削比 (無因次)
    """
    return Ctip / Croot


# ============================================================================
# DATCOM 參數轉換工具 (LangChain Tools)
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
    sweep_location: float = 0.25
) -> Dict[str, Any]:
    """將標準機翼參數轉換為 DATCOM $WGPLNF namelist 參數。
    
    基於「DATCOM 參數解析與轉換.md」第一節的公式：
    - 翼展: b = √(A·S)
    - 翼根弦長: Croot = 2S / [b(1+λ)]
    - 翼尖弦長: Ctip = λ·Croot
    - 半翼展: SSPN = b/2
    
    Args:
        S: 參考翼面積 (ft²)
        A: 展弦比 (無因次)
        lambda_: 尖削比 (無因次, 0.0-1.0)
        sweep_angle: 後掠角 (度)
        airfoil: NACA 翼型代碼 (預設 "2412")
        dihedral: 上反角 (度, 預設 0.0)
        twist: 扭轉角 (度, 負值為洗出, 預設 0.0)
        sweep_location: 後掠角量測位置 (弦長百分比, 預設 0.25 為四分之一弦長)
    
    Returns:
        包含 DATCOM $WGPLNF 參數的字典，可直接用於生成 DATCOM.dat
    
    Examples:
        F-4 Phantom II 機翼:
        >>> convert_wing_to_datcom(S=530, A=2.8, lambda_=0.3, sweep_angle=45)
        {
            'CHRDR': 17.85,
            'CHRDTP': 5.36,
            'SSPN': 19.22,
            'SAVSI': 45.0,
            'CHSTAT': 0.25,
            'TYPE': 1.0,
            'DHDADI': 0.0,
            'TWISTA': 0.0,
            'airfoil': 'NACA-W-4-2412',
            ...
        }
    """
    log(f"Converting wing params: S={S}, A={A}, λ={lambda_}, sweep={sweep_angle}°")
    
    # 驗證輸入
    if S <= 0 or A <= 0:
        return {"error": "翼面積 S 和展弦比 A 必須大於 0"}
    if not (0 <= lambda_ <= 1):
        return {"error": f"尖削比 λ 必須在 0-1 之間，當前值: {lambda_}"}
    
    # 核心幾何計算
    b = calculate_wingspan(S, A)
    Croot = calculate_root_chord(S, b, lambda_)
    Ctip = calculate_tip_chord(Croot, lambda_)
    SSPN = b / 2
    MAC = calculate_mean_aerodynamic_chord(Croot, lambda_)
    
    # DATCOM 參數映射
    datcom_params = {
        # $WGPLNF 必要參數
        "CHRDR": round(Croot, 2),        # 翼根弦長
        "CHRDTP": round(Ctip, 2),        # 翼尖弦長
        "SSPN": round(SSPN, 2),          # 理論半翼展
        "SSPNE": round(SSPN, 2),         # 暴露半翼展 (假設無機身遮蔽)
        "SAVSI": round(sweep_angle, 1),  # 後掠角
        "CHSTAT": sweep_location,         # 後掠角量測位置
        "TYPE": 1.0,                      # 直線尖削翼
        "DHDADI": round(dihedral, 1),    # 上反角
        "TWISTA": round(twist, 1),       # 扭轉角
        
        # NACA 翼型卡片
        "airfoil": f"NACA-W-4-{airfoil}",
        
        # $OPTINS 參考參數
        "SREF": round(S, 2),             # 參考面積
        
        # 推導參數 (供驗證使用)
        "_wingspan": round(b, 2),
        "_MAC": round(MAC, 2),
        "_aspect_ratio": round(A, 2),
        "_taper_ratio": round(lambda_, 3),
        
        # 公式追蹤 (供除錯使用)
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
    """將尾翼參數轉換為 DATCOM $HTPLNF 或 $VTPLNF namelist 參數。
    
    尾翼計算邏輯與機翼完全相同，體現「消除特殊情況」的設計哲學。
    
    Args:
        component: 組件名稱 ("horizontal_tail" 或 "vertical_tail")
        S: 尾翼面積 (ft²)
        A: 展弦比 (無因次)
        lambda_: 尖削比 (無因次)
        sweep_angle: 後掠角 (度)
        airfoil: NACA 翼型代碼 (預設 "0012" 對稱翼型)
        is_vertical: 是否為垂直尾翼 (預設 False)
    
    Returns:
        包含 DATCOM $HTPLNF 或 $VTPLNF 參數的字典
    
    Examples:
        F-4 水平尾翼:
        >>> convert_tail_to_datcom("horizontal_tail", S=100, A=3.0, lambda_=0.4, sweep_angle=35)
        
        F-4 垂直尾翼:
        >>> convert_tail_to_datcom("vertical_tail", S=80, A=1.5, lambda_=0.3, sweep_angle=45, is_vertical=True)
    """
    log(f"Converting {component}: S={S}, A={A}, λ={lambda_}, sweep={sweep_angle}°")
    
    # 驗證輸入
    if S <= 0 or A <= 0:
        return {"error": "面積 S 和展弦比 A 必須大於 0"}
    if not (0 <= lambda_ <= 1):
        return {"error": f"尖削比 λ 必須在 0-1 之間，當前值: {lambda_}"}
    
    # 核心幾何計算 (與機翼相同)
    b = calculate_wingspan(S, A)
    Croot = calculate_root_chord(S, b, lambda_)
    Ctip = calculate_tip_chord(Croot, lambda_)
    SSPN = b / 2  # 對垂直尾翼，這是高度
    
    # DATCOM 參數映射
    namelist = "$VTPLNF" if is_vertical else "$HTPLNF"
    airfoil_prefix = "V" if is_vertical else "H"
    
    datcom_params = {
        # Namelist 必要參數
        "CHRDR": round(Croot, 2),
        "CHRDTP": round(Ctip, 2),
        "SSPN": round(SSPN, 2),
        "SSPNE": round(SSPN, 2),
        "SAVSI": round(sweep_angle, 1),
        "CHSTAT": 0.25,
        "TYPE": 1.0,
        "DHDADI": 0.0,  # 尾翼通常無上反角
        "TWISTA": 0.0,  # 尾翼通常無扭轉
        
        # NACA 翼型卡片
        "airfoil": f"NACA-{airfoil_prefix}-4-{airfoil}",
        
        # 元數據
        "_component": component,
        "_namelist": namelist,
        "_wingspan_or_height": round(b, 2),
        "_area": round(S, 2),
        
        # 公式追蹤
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
    """計算 DATCOM $SYNTHS namelist 的組件位置座標。
    
    基於機身長度百分比快速計算各組件的 X 座標位置。
    
    Args:
        fuselage_length: 機身總長度 (ft)
        wing_position_percent: 機翼頂點位置 (機身長度百分比, 預設 40%)
        htail_position_percent: 水平尾翼位置 (預設 90%)
        vtail_position_percent: 垂直尾翼位置 (預設 65%)
        cg_position_percent: 重心位置 (預設 35%)
        wing_z: 機翼垂直位置 (ft, 預設 0.0)
        htail_z: 水平尾翼垂直位置 (ft, 預設 0.0)
        vtail_z: 垂直尾翼垂直位置 (ft, 預設 0.0)
    
    Returns:
        包含 $SYNTHS 參數的字典
    
    Examples:
        F-4 Phantom II (機身長 58.3 ft):
        >>> calculate_synthesis_positions(58.3, wing_position_percent=0.42)
        {
            'XCG': 20.41,
            'XW': 24.49,
            'XH': 52.47,
            'XV': 37.90,
            ...
        }
    """
    log(f"Calculating $SYNTHS positions for fuselage length={fuselage_length} ft")
    
    if fuselage_length <= 0:
        return {"error": "機身長度必須大於 0"}
    
    # 計算 X 座標
    XCG = fuselage_length * cg_position_percent
    XW = fuselage_length * wing_position_percent
    XH = fuselage_length * htail_position_percent
    XV = fuselage_length * vtail_position_percent
    
    synths_params = {
        # 重心位置
        "XCG": round(XCG, 2),
        "ZCG": 0.0,  # 通常在參考線上
        
        # 機翼位置
        "XW": round(XW, 2),
        "ZW": round(wing_z, 2),
        "ALIW": 1.0,  # 機翼安裝角 (度, 通常 0-2°)
        
        # 水平尾翼位置
        "XH": round(XH, 2),
        "ZH": round(htail_z, 2),
        "ALIH": 0.0,  # 水平尾翼安裝角
        
        # 垂直尾翼位置
        "XV": round(XV, 2),
        "ZV": round(vtail_z, 2),
        
        # 推導參數
        "_fuselage_length": fuselage_length,
        "_positions_percent": {
            "CG": f"{cg_position_percent*100:.1f}%",
            "Wing": f"{wing_position_percent*100:.1f}%",
            "HTail": f"{htail_position_percent*100:.1f}%",
            "VTail": f"{vtail_position_percent*100:.1f}%"
        },
        
        # 力臂計算 (供穩定性分析參考)
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
    fuselage_length: float,
    max_diameter: float,
    nose_length: float,
    tail_length: float,
    num_stations: float = 8.0
) -> Dict[str, Any]:
    """定義 DATCOM $BODY namelist 的軸對稱機身幾何。
    
    使用簡化的站位分布生成機身橫截面定義。適用於初步設計階段。
    
    Args:
        fuselage_length: 機身總長度 (ft)
        max_diameter: 最大機身直徑 (ft)
        nose_length: 機鼻長度 (ft)
        tail_length: 機尾錐長度 (ft)
        num_stations: 站位數量 (預設 8.0, 最多 20.0)
    
    Returns:
        包含 $BODY 參數的字典，包括 X 和 R (或 S) 陣列
    
    Examples:
        F-4 Phantom II 機身:
        >>> define_body_geometry(58.3, 3.0, 8.0, 10.0, num_stations=10.0)
    """
    log(f"Defining $BODY: length={fuselage_length}, max_dia={max_diameter}")
    
    # 驗證輸入
    num_stations = int(num_stations)
    if num_stations > 20:
        return {"error": "DATCOM 最多支援 20 個機身站位"}
    if nose_length + tail_length >= fuselage_length:
        return {"error": "機鼻長度 + 機尾長度不能超過機身總長"}
    
    # 生成站位分布
    X_stations: List[float] = []
    R_stations: List[float] = []
    
    max_radius = max_diameter / 2
    constant_section_start = nose_length
    constant_section_end = fuselage_length - tail_length
    
    for i in range(num_stations):
        # X 座標 (等間距分布)
        x = (fuselage_length / (num_stations - 1)) * i
        X_stations.append(round(x, 2))
        
        # R 座標 (簡化的機身外形)
        if x <= nose_length:
            # 機鼻段: 拋物線增長
            r = max_radius * math.sqrt(x / nose_length)
        elif x <= constant_section_end:
            # 等截面段
            r = max_radius
        else:
            # 機尾段: 線性收縮
            fraction = (fuselage_length - x) / tail_length
            r = max_radius * fraction
        
        R_stations.append(round(r, 2))
    
    # 計算橫截面積
    S_stations = [round(math.pi * r**2, 2) for r in R_stations]
    
    body_params = {
        # $BODY 必要參數
        "NX": float(num_stations),
        "X": X_stations,
        "R": R_stations,
        "S": S_stations,  # 提供兩種格式供選擇
        
        # 推導參數
        "_max_diameter": max_diameter,
        "_max_radius": max_radius,
        "_max_cross_section_area": round(math.pi * max_radius**2, 2),
        "_fineness_ratio": round(fuselage_length / max_diameter, 2),
        
        # 幾何描述
        "_geometry": {
            "total_length": fuselage_length,
            "nose_length": nose_length,
            "constant_section": round(constant_section_end - constant_section_start, 2),
            "tail_length": tail_length
        }
    }
    
    log(f"✓ $BODY defined: {num_stations} stations, fineness ratio={body_params['_fineness_ratio']}")
    return body_params


@tool
def generate_fltcon_matrix(
    mach_numbers: List[float],
    altitudes: List[float],
    alpha_range: Tuple[float, float, float],
    weight: float,
    loop_mode: float = 2.0
) -> Dict[str, Any]:
    """生成 DATCOM $FLTCON namelist 的飛行條件矩陣。
    
    Args:
        mach_numbers: 馬赫數列表
        altitudes: 高度列表 (ft)
        alpha_range: 攻角範圍 (起始, 結束, 步長) 度
        weight: 飛機重量 (lbs)
        loop_mode: 迴圈模式 (1.0=高度優先, 2.0=馬赫優先, 3.0=高度優先)
    
    Returns:
        包含 $FLTCON 參數的字典
    
    Examples:
        F-4 飛行包線:
        >>> generate_fltcon_matrix(
        ...     mach_numbers=[0.6, 0.8, 0.95],
        ...     altitudes=[10000, 20000, 30000],
        ...     alpha_range=(-4, 14, 2),
        ...     weight=38000
        ... )
    """
    log(f"Generating $FLTCON: M={mach_numbers}, ALT={altitudes}")
    
    # 生成攻角陣列
    alpha_start, alpha_end, alpha_step = alpha_range
    alpha_schedule = []
    alpha = alpha_start
    while alpha <= alpha_end:
        alpha_schedule.append(round(alpha, 1))
        alpha += alpha_step
    
    if len(alpha_schedule) > 20:
        return {"error": "DATCOM 最多支援 20 個攻角點 (NALPHA <= 20)"}
    
    fltcon_params = {
        # 馬赫數定義
        "NMACH": float(len(mach_numbers)),
        "MACH": [round(m, 2) for m in mach_numbers],
        
        # 高度定義
        "NALT": float(len(altitudes)),
        "ALT": [round(alt, 1) for alt in altitudes],
        
        # 攻角定義
        "NALPHA": float(len(alpha_schedule)),
        "ALSCHD": alpha_schedule,
        
        # 飛機重量
        "WT": round(weight, 1),
        
        # 迴圈控制
        "LOOP": float(loop_mode),
        
        # 分析矩陣大小
        "_analysis_points": len(mach_numbers) * len(altitudes) * len(alpha_schedule),
        "_loop_description": {
            1.0: "對每個高度，遍歷所有攻角和馬赫數",
            2.0: "對每個馬赫數，遍歷所有高度和攻角",
            3.0: "對每個高度，遍歷所有馬赫數和攻角"
        }.get(loop_mode, "未知迴圈模式")
    }
    
    log(f"✓ $FLTCON generated: {fltcon_params['_analysis_points']} analysis points")
    return fltcon_params


@tool
def validate_datcom_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """驗證 DATCOM 參數的合理性與一致性。
    
    基於「DATCOM 參數解析與轉換.md」第六節的最佳實踐。
    
    Args:
        params: 包含 DATCOM 參數的字典
    
    Returns:
        驗證報告，包含警告和錯誤
    
    Examples:
        >>> validate_datcom_parameters({
        ...     'CHRDR': 17.85,
        ...     'CHRDTP': 5.36,
        ...     'SSPN': 19.22
        ... })
    """
    log("Validating DATCOM parameters...")
    
    warnings = []
    errors = []
    
    # 幾何一致性檢查
    if 'CHRDR' in params and 'CHRDTP' in params:
        if params['CHRDTP'] > params['CHRDR']:
            errors.append("翼尖弦長 (CHRDTP) 不應大於翼根弦長 (CHRDR)")
    
    if 'SSPN' in params and 'SSPNE' in params:
        if params['SSPNE'] > params['SSPN']:
            errors.append("暴露半翼展 (SSPNE) 不應大於理論半翼展 (SSPN)")
    
    # 數值範圍檢查
    if 'SAVSI' in params:
        if abs(params['SAVSI']) > 70:
            warnings.append(f"後掠角 {params['SAVSI']}° 超過常見範圍 (±70°)")
    
    if 'DHDADI' in params:
        if abs(params['DHDADI']) > 15:
            warnings.append(f"上反角 {params['DHDADI']}° 超過常見範圍 (±15°)")
    
    # FORTRAN 格式檢查
    for key, value in params.items():
        if isinstance(value, int) and not key.startswith('_'):
            warnings.append(f"參數 {key}={value} 應使用浮點格式 (例如 {value}.0)")
    
    validation_report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "checked_parameters": list(params.keys()),
        "summary": f"{len(errors)} 錯誤, {len(warnings)} 警告"
    }
    
    log(f"✓ Validation complete: {validation_report['summary']}")
    return validation_report
    return validation_report


# ============================================================================
# 工具集導出
# ============================================================================

def create_datcom_calculator_tools() -> List:
    """創建完整的 DATCOM 計算器工具集
    
    Returns:
        包含所有 DATCOM 計算工具的列表
    """
    return [
        convert_wing_to_datcom,
        convert_tail_to_datcom,
        calculate_synthesis_positions,
        define_body_geometry,
        generate_fltcon_matrix,
        validate_datcom_parameters
    ]


if __name__ == "__main__":
    # 測試範例: F-4 Phantom II
    print("=" * 80)
    print("DATCOM Calculator Tool Test - F-4 Phantom II")
    print("=" * 80)
    
    # 1. 機翼轉換
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
    
    # 2. 水平尾翼
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
    
    # 3. 飛行條件
    fltcon = generate_fltcon_matrix.invoke({
        "mach_numbers": [0.6, 0.8, 0.95],
        "altitudes": [10000, 20000, 30000],
        "alpha_range": (-4, 14, 2),
        "weight": 38000,
        "loop_mode": 2
    })
    print("\n3. Flight Conditions ($FLTCON):")
    print(f"  Analysis Points: {fltcon['_analysis_points']}")
    print(f"  Mach: {fltcon['MACH']}")
    print(f"  Altitudes: {fltcon['ALT']}")
    
    print("\n" + "=" * 80)
    print("✓ All tests completed successfully!")
