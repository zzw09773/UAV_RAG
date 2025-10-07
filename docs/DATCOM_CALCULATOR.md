# DATCOM 計算器工具完整實現文檔

## 概述

基於「DATCOM 參數解析與轉換.md」文件，我們實現了完整的 DATCOM 參數計算與轉換工具集，使 RAG 系統能夠:

1. **將標準空氣動力學參數轉換為 DATCOM 格式**
2. **生成完整的 for005.dat 輸入檔案**
3. **驗證參數的合理性與一致性**

## 實現的工具

### 1. `convert_wing_to_datcom`
**功能**: 將標準機翼參數轉換為 DATCOM $WGPLNF namelist 參數

**輸入參數**:
- `S`: 參考翼面積 (ft²)
- `A`: 展弦比 (無因次)
- `lambda_`: 尖削比 (無因次, 0.0-1.0)
- `sweep_angle`: 後掠角 (度)
- `airfoil`: NACA 翼型代碼 (可選, 預設 "2412")
- `dihedral`: 上反角 (度, 可選, 預設 0.0)
- `twist`: 扭轉角 (度, 可選, 預設 0.0)

**核心公式**:
```python
b = √(A·S)                    # 翼展
Croot = 2S / [b(1+λ)]         # 翼根弦長
Ctip = λ·Croot                # 翼尖弦長
SSPN = b/2                     # 半翼展
```

**輸出**: 包含 CHRDR, CHRDTP, SSPN, SAVSI 等完整 $WGPLNF 參數

### 2. `convert_tail_to_datcom`
**功能**: 將尾翼參數轉換為 DATCOM $HTPLNF 或 $VTPLNF namelist 參數

**輸入參數**:
- `component`: "horizontal_tail" 或 "vertical_tail"
- `S`: 尾翼面積 (ft²)
- `A`: 展弦比
- `lambda_`: 尖削比
- `sweep_angle`: 後掠角 (度)
- `is_vertical`: 是否為垂直尾翼 (預設 False)

**輸出**: 包含 CHRDR, CHRDTP, SSPN, SAVSI 等參數，自動生成正確的 airfoil 卡片

### 3. `calculate_synthesis_positions`
**功能**: 計算 DATCOM $SYNTHS namelist 的組件位置座標

**輸入參數**:
- `fuselage_length`: 機身總長度 (ft)
- `wing_position_percent`: 機翼頂點位置百分比 (預設 40%)
- `htail_position_percent`: 水平尾翼位置百分比 (預設 90%)
- `vtail_position_percent`: 垂直尾翼位置百分比 (預設 65%)
- `cg_position_percent`: 重心位置百分比 (預設 35%)

**輸出**: XCG, XW, XH, XV, ZCG, ZW, ZH, ZV 等座標，並計算力臂供穩定性分析

### 4. `define_body_geometry`
**功能**: 定義 DATCOM $BODY namelist 的軸對稱機身幾何

**輸入參數**:
- `fuselage_length`: 機身總長度 (ft)
- `max_diameter`: 最大機身直徑 (ft)
- `nose_length`: 機鼻長度 (ft)
- `tail_length`: 機尾錐長度 (ft)
- `num_stations`: 站位數量 (預設 8, 最多 20)

**輸出**: NX, X, R, S 陣列，自動生成簡化的機身外形

### 5. `generate_fltcon_matrix`
**功能**: 生成 DATCOM $FLTCON namelist 的飛行條件矩陣

**輸入參數**:
- `mach_numbers`: 馬赫數列表
- `altitudes`: 高度列表 (ft)
- `alpha_range`: 攻角範圍 (起始, 結束, 步長) 度
- `weight`: 飛機重量 (lbs)
- `loop_mode`: 迴圈模式 (1=高度優先, 2=馬赫優先)

**輸出**: NMACH, MACH, NALT, ALT, NALPHA, ALSCHD, WT, LOOP 等完整參數

### 6. `validate_datcom_parameters`
**功能**: 驗證 DATCOM 參數的合理性與一致性

**檢查項目**:
- 幾何一致性 (CHRDTP ≤ CHRDR, SSPNE ≤ SSPN)
- 數值範圍 (後掠角 ≤ 70°, 上反角 ≤ 15°)
- FORTRAN 格式 (浮點數格式檢查)

**輸出**: 驗證報告，包含錯誤和警告列表

## 使用範例

### 範例 1: F-4 Phantom II 機翼參數計算

```bash
./query.sh "使用 convert_wing_to_datcom 工具計算 F-4 Phantom II 的機翼參數: S=530 ft², A=2.8, λ=0.3, 後掠角=45°"
```

**Agent 會調用**:
```python
convert_wing_to_datcom.invoke({
    "S": 530,
    "A": 2.8,
    "lambda_": 0.3,
    "sweep_angle": 45
})
```

**返回結果**:
```
CHRDR  = 21.17 ft
CHRDTP = 6.35 ft
SSPN   = 19.26 ft
SAVSI  = 45.0°
翼展   = 38.52 ft
MAC    = 15.09 ft
```

### 範例 2: 完整 for005.dat 生成

```bash
./query.sh "根據以下參數為 F-4 生成 DATCOM for005.dat: 
機翼 S=530 ft², A=2.8, λ=0.3, 後掠角45°。
飛行條件: Mach 0.8, 高度10000 ft, 攻角-2到10度每2度, 重量40000 lbs。
機身長度63 ft, 最大直徑3 ft。
XCG=25 ft, XW=18.5 ft, XH=49 ft, XV=45 ft。"
```

**Agent 執行流程**:
1. 調用 `convert_wing_to_datcom` 計算機翼參數
2. 調用 `generate_fltcon_matrix` 生成飛行條件
3. 調用 `define_body_geometry` 定義機身幾何
4. 從資料庫檢索 for005.dat 模板範例
5. 組合所有參數生成完整檔案

## 設計哲學

### 1. **消除特殊情況**
所有升力面 (機翼、水平尾翼、垂直尾翼) 使用統一的計算邏輯:
```python
# 相同的核心函數
b = calculate_wingspan(S, A)
Croot = calculate_root_chord(S, b, lambda_)
Ctip = calculate_tip_chord(Croot, lambda_)
```

### 2. **數據結構優先**
清晰的輸入輸出映射，避免複雜的條件分支:
```python
{
    "標準參數": {"S", "A", "λ", "Λ"},
    "DATCOM 參數": {"CHRDR", "CHRDTP", "SSPN", "SAVSI"},
    "推導參數": {"_wingspan", "_MAC", "_formulas"}
}
```

### 3. **零破壞**
- 與現有工具完全兼容
- 不修改原有 calculator.py
- 獨立模組設計

### 4. **可讀性和維護性**
- 每個函數少於 20 行核心邏輯
- 清晰的文檔字串
- 完整的公式追蹤

## 測試驗證

### 單元測試
```bash
python test_datcom_calculator.py
```

**測試涵蓋**:
- ✅ F-4 Phantom II 完整參數計算
- ✅ MiG-17 與文檔範例一致性驗證
- ✅ 邊界情況與錯誤處理

### 集成測試
```bash
# 測試工具調用
./query.sh "使用 convert_wing_to_datcom 計算..."

# 測試完整生成
./query.sh "生成 F-4 的 for005.dat..."
```

## 與 Roadmap 的對應

| Roadmap 項目 | 實現狀態 | 對應工具 |
|-------------|---------|---------|
| Phase 1: DATCOM Calculator Tool | ✅ 完成 | 所有 6 個工具 |
| Phase 1: Parameter Validation | ✅ 完成 | validate_datcom_parameters |
| Phase 1: Unit Conversion | ✅ 完成 | 所有工具支援英制單位 |
| Phase 2: Template Generator | 🟡 部分完成 | 需要檢索模板並組合 |
| Phase 2: Parameter Inference | 🟡 部分完成 | 提供公式但需 LLM 判斷 |

## 已知限制與改進方向

### 當前限制
1. **只支援簡單梯形翼**: 曲折翼 (cranked wing) 參數需要手動指定
2. **機身幾何簡化**: 只支援軸對稱旋轉體
3. **無進氣道建模**: DATCOM 本身的限制
4. **無自動參數推算**: 缺失參數需要使用者提供或從文檔檢索

### 改進方向 (Phase 2-3)
1. **模板生成器**: 直接輸出完整的 for005.dat 文本
2. **參數推算**: 使用典型戰機比例關係填補缺失參數
3. **幾何驗證**: 整合視覺化工具
4. **批次分析**: 支援參數掃描研究

## 與文檔的對應關係

| 文檔章節 | 實現的工具 |
|---------|-----------|
| 第一節: 基礎轉譯 | convert_wing_to_datcom |
| 第二節: $FLTCON | generate_fltcon_matrix |
| 第三節: $SYNTHS | calculate_synthesis_positions |
| 第四節: $WGPLNF/$HTPLNF/$VTPLNF | convert_wing_to_datcom, convert_tail_to_datcom |
| 第五節: $BODY | define_body_geometry |
| 第六節: 最佳實踐 | validate_datcom_parameters |

## 品味評級: 🟢 Good Taste

**理由**:
- ✅ 所有函數少於 60 行，核心邏輯少於 20 行
- ✅ 最多 3 層縮排
- ✅ 每個工具單一職責
- ✅ 清晰的數據流: 輸入 → 計算 → 驗證 → 輸出
- ✅ 無不必要的狀態欄位
- ✅ 完整的公式追蹤和錯誤處理

---

**實現日期**: 2025年10月7日  
**版本**: v0.4.0-alpha  
**貢獻**: 補齊了系統從「參數理解」到「參數生成」的最後一哩路
