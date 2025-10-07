# ⚡ Quick Start - 立即行動指南

**基於**: 專案審查報告 (`docs/PROJECT_AUDIT.md`) 和發展路線圖 (`ROADMAP.md`)

---

## 🎯 優先級矩陣

```
重要且緊急 (立即執行)    | 重要但不緊急 (計劃執行)
---------------------------|---------------------------
🔴 添加測試              | 🟡 效能優化
🔴 安全強化              | 🟡 Web UI
🔴 補充文件              | 🟡 對話記憶
                         |
不重要但緊急 (委派)      | 不重要不緊急 (忽略)
---------------------------|---------------------------
🟢 程式碼格式化          | ⚪ 過度優化
🟢 Linting 修復          | ⚪ 花哨功能
```

---

## 📅 第一週行動計劃 (10/7 - 10/13)

### Day 1: 設置測試環境 ⏰ 3-4 小時

**目標**: 建立測試基礎設施

**步驟**:

1. **安裝測試依賴**
   ```bash
   cd /home/c1147259/桌面/RAG
   
   # 更新 requirements.txt
   echo "
# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.0
pytest-timeout>=2.1.0
   " >> requirements.txt
   
   # 安裝
   pip install -r requirements.txt
   ```

2. **創建測試目錄結構**
   ```bash
   mkdir -p tests/{unit,integration,e2e,fixtures}
   touch tests/__init__.py
   touch tests/conftest.py
   ```

3. **配置 pytest**
   ```bash
   cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=rag_system
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=60
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
EOF
   ```

4. **創建測試配置**
   ```python
   # tests/conftest.py
   import pytest
   from unittest.mock import Mock
   
   @pytest.fixture
   def mock_llm():
       """Mock LLM for testing"""
       return Mock()
   
   @pytest.fixture
   def sample_documents():
       """Sample documents for testing"""
       return [
           {"content": "升力公式: L = CL * q * S", "metadata": {"section": "公式"}},
           {"content": "阻力公式: D = CD * q * S", "metadata": {"section": "公式"}},
       ]
   ```

**驗收**: 
- ✅ `pytest --version` 可執行
- ✅ 測試目錄結構建立
- ✅ `pytest.ini` 配置完成

---

### Day 2: 第一批單元測試 ⏰ 4-5 小時

**目標**: 測試覆蓋率達到 20%

**步驟**:

1. **測試計算器**
   ```python
   # tests/unit/test_calculator.py
   import pytest
   from rag_system.tool.calculator import create_calculator_tool
   
   @pytest.mark.unit
   def test_calculator_basic():
       """測試基本計算"""
       calc = create_calculator_tool()
       result = calc.invoke({"expression": "2 + 2"})
       assert "4" in result
   
   @pytest.mark.unit
   def test_calculator_math_functions():
       """測試數學函數"""
       calc = create_calculator_tool()
       result = calc.invoke({"expression": "math.sqrt(16)"})
       assert "4" in result
   
   @pytest.mark.unit
   def test_calculator_invalid_expression():
       """測試非法表達式"""
       calc = create_calculator_tool()
       result = calc.invoke({"expression": "import os"})
       assert "錯誤" in result or "error" in result.lower()
   
   @pytest.mark.unit
   def test_calculator_complex():
       """測試複雜計算"""
       calc = create_calculator_tool()
       # 動壓公式: q = 0.5 * ρ * V^2
       result = calc.invoke({"expression": "0.5 * 1.225 * (20**2)"})
       assert "245" in result
   ```

2. **測試文本清理**
   ```python
   # tests/unit/test_chunking.py
   import pytest
   from rag_system.build.chunking import clean_text
   
   @pytest.mark.unit
   def test_clean_text_basic():
       """測試基本清理"""
       text = "  多餘  空格  "
       result = clean_text(text)
       assert result == "多餘 空格"
   
   @pytest.mark.unit
   def test_clean_text_preserves_latex():
       """測試保留 LaTeX"""
       text = "公式: $F = ma$ 和 $$E = mc^2$$"
       result = clean_text(text)
       assert "$F = ma$" in result
       assert "$$E = mc^2$$" in result
   
   @pytest.mark.unit
   def test_clean_text_newlines():
       """測試換行處理"""
       text = "第一行\n\n\n\n第二行"
       result = clean_text(text)
       assert result == "第一行\n\n第二行"
   ```

3. **執行測試**
   ```bash
   pytest tests/unit -v
   pytest --cov=rag_system --cov-report=html
   
   # 查看覆蓋率報告
   open htmlcov/index.html  # macOS
   # xdg-open htmlcov/index.html  # Linux
   ```

**驗收**:
- ✅ 至少 8 個測試通過
- ✅ 測試覆蓋率 ≥ 20%
- ✅ 無明顯錯誤

---

### Day 3: 安全改造計算器 ⏰ 3-4 小時

**目標**: 替換 `eval()` 為安全替代方案

**步驟**:

1. **安裝 sympy**
   ```bash
   pip install sympy timeout-decorator
   ```

2. **改造計算器** (編輯 `rag_system/tool/calculator.py`)
   ```python
   """Python 計算工具，用於數學運算和參數推算"""
   from typing import Callable
   from langchain.tools import tool
   import math
   from sympy import sympify, N
   import timeout_decorator
   from ..common import log
   
   
   def create_calculator_tool() -> Callable:
       """創建 Python 計算工具"""
       
       @tool
       @timeout_decorator.timeout(5, timeout_exception=TimeoutError)
       def python_calculator(expression: str) -> str:
           """執行數學計算或參數推算。
           
           使用 sympy 進行安全計算,支援基本數學運算和函數。
           
           Args:
               expression: 數學表達式
           
           Returns:
               計算結果或錯誤訊息
           """
           log(f"Calculator executing: {expression}")
           
           # 長度限制
           if len(expression) > 500:
               return "錯誤: 表達式過長 (最多 500 字符)"
           
           # 檢查危險字符
           dangerous = ['__', 'import', 'exec', 'eval', 'open', 'file']
           if any(d in expression.lower() for d in dangerous):
               return "錯誤: 表達式包含非法關鍵字"
           
           try:
               # 使用 sympy 安全計算
               result = N(sympify(expression))
               return f"計算結果: {float(result)}"
           
           except TimeoutError:
               return "錯誤: 計算超時 (> 5 秒)"
           except Exception as e:
               log(f"Calculator error: {e}")
               return f"計算錯誤: {str(e)}"
       
       return python_calculator
   ```

3. **測試安全性**
   ```python
   # tests/unit/test_calculator_security.py
   import pytest
   from rag_system.tool.calculator import create_calculator_tool
   
   @pytest.mark.unit
   def test_calculator_blocks_import():
       """測試阻止 import"""
       calc = create_calculator_tool()
       result = calc.invoke({"expression": "import os"})
       assert "錯誤" in result or "非法" in result
   
   @pytest.mark.unit
   def test_calculator_blocks_eval():
       """測試阻止 eval"""
       calc = create_calculator_tool()
       result = calc.invoke({"expression": "eval('2+2')"})
       assert "錯誤" in result
   
   @pytest.mark.unit
   def test_calculator_length_limit():
       """測試長度限制"""
       calc = create_calculator_tool()
       result = calc.invoke({"expression": "1+" * 300})
       assert "過長" in result
   ```

**驗收**:
- ✅ 使用 sympy 替代 eval
- ✅ 添加超時保護
- ✅ 危險字符檢查
- ✅ 安全測試通過

---

### Day 4: 創建環境範本 ⏰ 2-3 小時

**目標**: 補充部署文件

**步驟**:

1. **創建 `.env.example`**
   ```bash
   cat > .env.example << 'EOF'
# ============================================================================
# OpenAI API 配置
# ============================================================================
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1

# ============================================================================
# 模型配置
# ============================================================================
EMBED_MODEL_NAME=nvidia/nv-embed-v2
CHAT_MODEL_NAME=openai/gpt-oss-20b
TEMPERATURE=0

# ============================================================================
# 資料庫配置
# ============================================================================
DB_HOST=localhost
DB_PORT=5433
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
PG_PORT=5433

# ============================================================================
# 系統配置
# ============================================================================
ENV=development  # production, staging, development
LOG_LEVEL=INFO   # DEBUG, INFO, WARNING, ERROR
VERIFY_SSL=true  # 生產環境必須為 true

# ============================================================================
# 檢索配置
# ============================================================================
DEFAULT_TOP_K=10
DEFAULT_CONTENT_MAX_LENGTH=800

# ============================================================================
# Redis 快取 (可選,Phase 2)
# ============================================================================
# REDIS_URL=redis://localhost:6379/0
# CACHE_TTL=86400

# ============================================================================
# 監控配置 (可選,Phase 3)
# ============================================================================
# PROMETHEUS_PORT=9090
# GRAFANA_PORT=3000
EOF
   ```

2. **創建環境驗證腳本**
   ```bash
   cat > scripts/verify_env.sh << 'EOF'
#!/bin/bash
# 環境驗證腳本

set -e

echo "🔍 驗證環境配置..."

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查必要環境變數
required_vars=(
    "OPENAI_API_KEY"
    "OPENAI_API_BASE"
    "DB_HOST"
    "DB_PORT"
    "DB_NAME"
    "DB_USER"
    "DB_PASSWORD"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
        echo -e "${RED}❌ $var 未設置${NC}"
    else
        echo -e "${GREEN}✅ $var 已設置${NC}"
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "\n${RED}錯誤: 以下環境變數未設置:${NC}"
    printf '%s\n' "${missing_vars[@]}"
    echo -e "\n請複製 .env.example 為 .env 並填入正確值:"
    echo "cp .env.example .env"
    exit 1
fi

# 測試資料庫連接
echo -e "\n🗄️  測試資料庫連接..."
if docker exec rag_db pg_isready -U $DB_USER > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 資料庫連接正常${NC}"
else
    echo -e "${YELLOW}⚠️  資料庫未啟動或無法連接${NC}"
    echo "請執行: docker compose up -d pgvector"
fi

# 測試 Python 環境
echo -e "\n🐍 測試 Python 環境..."
if python -c "import rag_system; print('OK')" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Python 模組可導入${NC}"
else
    echo -e "${RED}❌ Python 模組導入失敗${NC}"
    echo "請執行: pip install -r requirements.txt"
    exit 1
fi

echo -e "\n${GREEN}🎉 環境驗證通過!${NC}"
EOF
   
   chmod +x scripts/verify_env.sh
   ```

3. **測試驗證腳本**
   ```bash
   # 創建 .env (如果不存在)
   cp .env.example .env
   
   # 執行驗證
   ./scripts/verify_env.sh
   ```

**驗收**:
- ✅ `.env.example` 創建
- ✅ 驗證腳本可執行
- ✅ 文件清晰易懂

---

### Day 5: 開始 DATCOM 文件 ⏰ 3-4 小時

**目標**: 創建 `docs/DATCOM_USAGE.md`

**步驟**:

1. **創建文件框架**
   ```bash
   cat > docs/DATCOM_USAGE.md << 'EOF'
# DATCOM 整合使用指南

**目標讀者**: UAV 戰機設計工程師  
**更新日期**: 2025-10-07

---

## 📖 目錄

1. [DATCOM 簡介](#datcom-簡介)
2. [系統功能](#系統功能)
3. [快速開始](#快速開始)
4. [使用案例](#使用案例)
5. [氣動參數查詢](#氣動參數查詢)
6. [公式計算](#公式計算)
7. [最佳實踐](#最佳實踐)
8. [常見問題](#常見問題)

---

## DATCOM 簡介

### 什麼是 DATCOM?

DATCOM (Data Compendium) 是美國空軍開發的空氣動力學分析工具,用於:
- 預測飛行器的氣動特性
- 計算升力、阻力、力矩係數
- 評估穩定性與操控性

### 本系統的作用

UAV RAG 系統整合 DATCOM 文件,提供:
- 🔍 **智能檢索**: 快速找到相關設計資料
- 📊 **參數計算**: 自動計算氣動參數
- 📚 **知識庫**: 歷史設計案例參考
- 🤖 **AI 助手**: 回答技術問題

---

## 系統功能

### 1. 設計領域路由

系統自動識別問題所屬領域:
- 空氣動力學
- 飛控系統
- 結構設計
- 動力系統

### 2. 文件檢索

從以下資料中檢索:
- DATCOM 技術手冊
- 風洞測試數據
- 歷史設計文件
- 飛行測試報告

### 3. 公式計算

支援自動計算:
- 動壓: q = 0.5 * ρ * V²
- 升力: L = CL * q * S
- 阻力: D = CD * q * S
- 力矩: M = Cm * q * S * c

---

## 快速開始

### 環境準備

```bash
# 1. 啟動資料庫
docker compose up -d pgvector

# 2. 建立索引 (首次使用)
cd rag_system
python -m rag_system.build.indexer \
    --input documents/DATCOM\ 範例與測試情境建立.docx \
    --embed --reset-collection

# 3. 驗證環境
../scripts/verify_env.sh
```

### 第一次查詢

```bash
# CLI 查詢
./query.sh "無人機升力係數計算公式是什麼?"

# Python API
python -c "
from rag_system.query_rag_pg import RagApplication
import argparse

args = argparse.Namespace(
    query='升力係數計算',
    conn='postgresql://postgres:postgres@localhost:5433/postgres',
    # ... 其他配置
)
app = RagApplication(args)
result = app.run()
print(result)
"
```

---

## 使用案例

### 案例 1: 查詢升力公式

**問題**: 「無人機升力計算公式是什麼?」

**系統流程**:
1. 路由到「空氣動力學」領域
2. 檢索相關文件
3. 提取公式: L = CL * q * S
4. 生成答案並引用來源

**回答範例**:
```
升力計算公式為:

L = CL * q * S

其中:
- L: 升力 (N)
- CL: 升力係數 (無因次)
- q: 動壓 (Pa) = 0.5 * ρ * V²
- S: 翼面積 (m²)

(來源: DATCOM 範例與測試情境建立.docx, 第 2.1 節)
```

### 案例 2: 參數計算

**問題**: 「無人機在海平面飛行,速度 20 m/s,空氣密度 1.225 kg/m³,計算動壓。」

**系統流程**:
1. 識別需要計算
2. 調用計算器工具
3. 執行: 0.5 * 1.225 * (20**2)
4. 返回結果

**回答範例**:
```
根據動壓公式 q = 0.5 * ρ * V²:

q = 0.5 × 1.225 × 20²
  = 0.5 × 1.225 × 400
  = 245 Pa

(計算器結果: 245.0)
```

### 案例 3: 設計參數查詢

**問題**: 「F-16 的升力係數範圍是多少?」

**系統流程**:
1. 路由到「空氣動力學」
2. 檢索 F-16 相關數據
3. 提取升力係數範圍
4. 生成答案

**回答範例**:
```
根據風洞測試數據,F-16 的升力係數 (CL) 範圍:

- 巡航狀態: CL ≈ 0.3 - 0.5
- 起飛/降落: CL ≈ 1.0 - 1.5
- 最大升力: CL_max ≈ 1.8 (有襟翼)

攻角超過 25° 時會啟動失速限制器。

(來源: F-16 飛控系統文件, Line 127)
```

---

## 氣動參數查詢

### 常用查詢模式

1. **公式查詢**
   - 「升力公式是什麼?」
   - 「如何計算阻力?」
   - 「動壓的定義」

2. **參數查詢**
   - 「升力係數的典型範圍」
   - 「雷諾數對阻力的影響」
   - 「翼型選擇建議」

3. **案例查詢**
   - 「類似無人機的設計參數」
   - 「歷史設計經驗」
   - 「常見問題解決方案」

### 提問技巧

**✅ 良好的提問**:
- 「計算升力,機翼面積 30m²,動壓 500Pa,升力係數 1.2」
- 「NACA 2412 翼型的升阻比範圍」
- 「攻角 10 度時的升力係數」

**❌ 不良的提問**:
- 「幫我設計飛機」(過於籠統)
- 「最好的無人機」(主觀問題)
- 「XXX」(無意義輸入)

---

## 公式計算

### 支援的計算

#### 1. 基本氣動公式

```python
# 動壓
q = 0.5 * ρ * V²

# 升力
L = CL * q * S

# 阻力
D = CD * q * S

# 升阻比
L_D_ratio = CL / CD
```

#### 2. 幾何參數

```python
# 翼展 (給定面積和展弦比)
b = sqrt(S * AR)

# 平均氣動弦長
MAC = S / b

# 錐度比相關
# ...
```

#### 3. 單位轉換

```python
# 速度: m/s → km/h
v_kmh = v_ms * 3.6

# 壓力: Pa → kPa
p_kpa = p_pa / 1000

# 角度: degree → radian
rad = deg * pi / 180
```

### 計算範例

**範例 1: 完整升力計算**

```
問題: 計算升力
- 空氣密度 ρ = 1.225 kg/m³
- 飛行速度 V = 30 m/s
- 翼面積 S = 20 m²
- 升力係數 CL = 1.0

步驟:
1. 計算動壓: q = 0.5 * 1.225 * 30² = 551.25 Pa
2. 計算升力: L = 1.0 * 551.25 * 20 = 11025 N

答案: 升力 L = 11025 N ≈ 11.0 kN
```

---

## 最佳實踐

### 1. 提問策略

- **明確具體**: 提供數值和單位
- **分步查詢**: 複雜問題拆分
- **驗證結果**: 檢查數量級合理性

### 2. 計算驗證

```python
# 檢查數量級
assert 100 < q < 10000, "動壓異常"

# 檢查單位
# 升力單位應為 N,範圍通常 100-100000
```

### 3. 來源追溯

- 記錄答案來源
- 交叉驗證多個資料
- 注意數據時效性

---

## 常見問題

### Q1: 找不到相關文件怎麼辦?

**A**: 
1. 嘗試不同關鍵字
2. 使用更通用的術語
3. 檢查是否已建立索引

### Q2: 計算結果不合理?

**A**:
1. 檢查輸入值和單位
2. 驗證公式是否正確
3. 查看計算器日誌

### Q3: 如何添加新文件?

**A**:
```bash
# 1. 放入文件
cp new_doc.docx rag_system/documents/

# 2. 建立索引
cd rag_system
python -m rag_system.build.indexer \
    --input documents/new_doc.docx \
    --embed --reset-collection
```

### Q4: 系統回答不準確?

**A**:
- 提供更詳細的問題描述
- 指定設計領域
- 使用技術術語
- 查看檢索到的文件是否相關

---

## 附錄

### A. DATCOM 參考資料

- [DATCOM 官方文件](https://www.pdas.com/datcom.html)
- [UAV 設計手冊](example.com)
- [空氣動力學基礎](example.com)

### B. 術語表

| 術語 | 英文 | 說明 |
|------|------|------|
| 升力 | Lift | L |
| 阻力 | Drag | D |
| 升力係數 | Lift Coefficient | CL |
| 阻力係數 | Drag Coefficient | CD |
| 動壓 | Dynamic Pressure | q |
| 攻角 | Angle of Attack | α (alpha) |

---

**需要協助?** 請參考 [故障排除指南](TROUBLESHOOTING.md)
EOF
   ```

2. **添加實際案例** (根據你的文件內容補充)

**驗收**:
- ✅ 文件框架完成
- ✅ 包含實際範例
- ✅ 格式清晰易讀

---

## 📊 第一週總結

### 預期成果

- ✅ 測試框架建立
- ✅ 20%+ 測試覆蓋率
- ✅ 計算器安全改造
- ✅ `.env.example` 創建
- ✅ 環境驗證腳本
- ✅ DATCOM 文件初稿

### 時間分配

| 任務 | 預估 | 優先級 |
|------|------|--------|
| Day 1: 測試環境 | 3-4h | 🔴 |
| Day 2: 單元測試 | 4-5h | 🔴 |
| Day 3: 安全改造 | 3-4h | 🔴 |
| Day 4: 環境範本 | 2-3h | 🟡 |
| Day 5: DATCOM文件 | 3-4h | 🟡 |
| **總計** | **15-20h** | |

### 驗收標準

```bash
# 1. 測試通過
pytest tests/ -v
# Expected: 8+ tests passing

# 2. 覆蓋率達標
pytest --cov=rag_system --cov-report=term
# Expected: Coverage >= 20%

# 3. 環境驗證通過
./scripts/verify_env.sh
# Expected: All checks passing

# 4. 安全測試通過
pytest tests/unit/test_calculator_security.py -v
# Expected: All security tests passing
```

---

## 🚀 下週預覽 (10/14 - 10/20)

### 目標: 測試覆蓋率 40%,文件補充

1. **更多單元測試**
   - Embedding 測試
   - 路由工具測試
   - 檢索工具測試

2. **整合測試**
   - Agent 流程測試
   - 向量搜尋測試

3. **文件完善**
   - 部署指南
   - API 參考
   - 故障排除

---

## 💡 Tips

### 時間管理

- 每天專注 2-3 小時即可
- 使用番茄工作法 (25 分鐘專注 + 5 分鐘休息)
- 遇到阻礙及時求助

### 品質保證

```bash
# 每天結束前執行
pytest tests/ --cov=rag_system
black rag_system/  # 格式化
flake8 rag_system/  # Linting
```

### 進度追蹤

```bash
# 創建進度檔案
echo "# Week 1 Progress

## Day 1 (10/7)
- [ ] 測試環境設置
- [ ] pytest 配置

## Day 2 (10/8)
- [ ] 計算器測試
- [ ] 文本清理測試

..." > PROGRESS.md
```

---

## 📞 需要協助?

- 🐛 **Bug**: 開 GitHub Issue
- 💡 **建議**: 開 Discussion
- 📧 **私密問題**: 聯繫維護者

---

**Let's get started! 🎯**
