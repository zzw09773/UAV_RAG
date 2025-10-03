# DATCOM 程式碼輔助系統使用指南

## 系統概述

DATCOM 程式碼輔助大師是專為戰機設計工程師打造的智慧檢索系統，透過探索過去的戰機設計資料、性能數據與程式碼，為新一代戰機的開發提供技術支援與洞見。

## 設計領域

系統支援五大戰機設計領域：

### 1. 空氣動力學 (Aerodynamics)
- **適用問題**：機翼設計、升力係數、阻力分析、風洞數據、氣動外型
- **資料類型**：CFD 分析報告、風洞測試數據、氣動力學模型、外型設計圖
- **範例問題**：
  - "F-16 的機翼升力係數在 Mach 0.9 時的數值？"
  - "如何降低超音速飛行時的波阻？"
  - "三角翼與梯形翼的升阻比比較數據"

### 2. 航電系統 (Avionics)
- **適用問題**：飛控系統、雷達、導航、感測器、航電架構、軟體程式碼
- **資料類型**：飛控原始碼、航電系統架構文件、感測器規格、雷達性能數據
- **範例問題**：
  - "F-16 飛控系統的攻角限制器程式碼"
  - "多功能雷達的目標追蹤演算法實作"
  - "導航系統的 Kalman Filter 參數設定"

### 3. 材料科學 (Materials Science)
- **適用問題**：複合材料、合金、結構強度、耐熱材料、材料測試數據
- **資料類型**：材料性能測試報告、複合材料配方、強度分析數據、疲勞測試結果
- **範例問題**：
  - "碳纖維複合材料在高溫環境下的強度衰減"
  - "鈦合金機身結構的疲勞壽命測試數據"
  - "隱形塗層的雷達反射率測試結果"

### 4. 武器掛載 (Weapons Integration)
- **適用問題**：飛彈掛架、武器整合、電子作戰系統、掛載配置
- **資料類型**：武器掛載手冊、掛架設計圖、電氣介面規格、投放測試數據
- **範例問題**：
  - "AIM-120 飛彈的掛架電氣介面規格"
  - "多掛點配置對飛行性能的影響分析"
  - "武器投放時的氣動力學干擾數據"

### 5. 推進系統 (Propulsion)
- **適用問題**：引擎性能、推力向量、燃油系統、進氣道設計
- **資料類型**：引擎性能曲線、推力測試數據、燃油消耗率、進氣道設計參數
- **範例問題**：
  - "F-16 引擎在不同高度的推力變化曲線"
  - "推力向量噴嘴的控制演算法"
  - "超音速進氣道的激波控制設計"

## 使用方式

### 基本查詢

```bash
# 使用便捷腳本（推薦）
./query.sh "F-16 飛控系統的攻角限制是多少？"

# 或直接調用
python -m rag_system.query_rag_pg -q "F-16 飛控系統的攻角限制是多少？"
```

### 指定設計領域

如果你已經知道問題屬於哪個領域，可以直接指定：

```bash
# 指定航電系統領域
./query.sh "攻角限制器的程式碼實作" --collection "航電系統"

# 指定空氣動力學領域
python -m rag_system.query_rag_pg \
  -q "升力係數的計算公式" \
  --collection "空氣動力學"
```

### 互動模式

進入互動模式可以連續提問：

```bash
python -m rag_system.query_rag_pg

# 進入後直接提問
> F-16 的最大攻角限制是多少？
> 推力向量系統如何運作？
> 顯示碳纖維材料的強度數據
> exit  # 離開
```

### 除錯模式

查看詳細的系統推理過程：

```bash
./query.sh "你的問題" --debug
```

除錯模式會顯示：
- 設計領域路由過程
- 文件檢索結果
- Agent 的思考推理步驟
- 工具調用詳情

## 工作流程

系統採用**兩步驟流程**：

### 第一步：設計領域路由

```
工程師問題 → design_area_router 工具
                     ↓
    分析問題關鍵字（機翼/飛控/材料/武器/引擎）
                     ↓
    選擇最相關的設計領域
                     ↓
    返回領域名稱（如『航電系統』）
```

### 第二步：檔案檢索

```
設計領域名稱 + 技術關鍵字 → retrieve_datcom_archive 工具
                                    ↓
            在指定領域的資料庫中進行向量檢索
                                    ↓
            返回相關的設計文件、數據、程式碼
                                    ↓
                LLM 分析並生成答案
                                    ↓
        附上來源引用（檔案名、章節、行號）
```

## 回答格式

系統的回答包含三個部分：

1. **技術答案**：基於檢索文件的精確資訊
2. **數據支持**：具體的數值、參數、程式碼片段
3. **來源引用**：明確的文件出處

### 範例回答

**問題**：F-16 的攻角限制器如何運作？

**回答**：
```
根據 F-16 的飛控系統原始碼 `f16_fcs_module.ada` 中 `calculate_aoa` 函數的註解，
當攻角超過 25 度時，系統會啟動限制器以防止失速。其關鍵參數 `max_aoa_limit`
設定為 25.5 度，限制器會在攻角達到 24 度時開始線性介入，在 25.5 度時完全限制
操縱面的進一步偏轉。

(來源: f16_fcs_module.ada, Line 127-145)
```

## 資料庫建立

### 準備文件

將設計文件、程式碼、測試報告放入對應目錄：

```bash
data/input/
├── aerodynamics/       # 空氣動力學文件
│   ├── wing_design.pdf
│   └── wind_tunnel_data.xlsx
├── avionics/          # 航電系統文件
│   ├── f16_fcs_module.ada
│   └── radar_specs.pdf
├── materials/         # 材料科學文件
├── weapons/           # 武器掛載文件
└── propulsion/        # 推進系統文件
```

### 建立索引

```bash
# 為空氣動力學領域建立索引
python -m rag_system.build.indexer \
  --file data/input/aerodynamics/wing_design.pdf \
  --collection "空氣動力學"

# 為航電系統領域建立索引
python -m rag_system.build.indexer \
  --file data/input/avionics/f16_fcs_module.ada \
  --collection "航電系統" \
  --chunk-strategy paragraph
```

### 批次建立

使用腳本批次處理所有文件：

```bash
#!/bin/bash

# 空氣動力學
for file in data/input/aerodynamics/*; do
    python -m rag_system.build.indexer --file "$file" --collection "空氣動力學"
done

# 航電系統
for file in data/input/avionics/*; do
    python -m rag_system.build.indexer --file "$file" --collection "航電系統"
done

# ... 其他領域
```

## 進階功能

### 1. 程式碼檢索

系統特別優化了程式碼檢索：

- **支援格式**：Ada, C, C++, Python, MATLAB
- **Metadata**：自動提取函數名、行號、註解
- **引用格式**：精確到行號

```bash
./query.sh "飛控系統中計算推力向量的函數實作"
# 返回: (來源: thrust_vector_control.c, Line 234-267)
```

### 2. 數據表格檢索

可以檢索性能數據表：

```bash
./query.sh "F-16 在不同高度的推力數據表"
# 返回完整的表格數據與來源
```

### 3. 跨領域查詢

系統會自動選擇最相關的領域，但某些問題可能涉及多個領域：

```bash
# 武器掛載對氣動力學的影響（可能路由到任一領域）
./query.sh "武器掛載如何影響飛機的升阻比？"
```

## 最佳實踐

### 提問技巧

✅ **好的問題**：
- "F-16 飛控系統的攻角限制器程式碼實作"
- "碳纖維複合材料在 800°C 下的拉伸強度"
- "AIM-120 飛彈掛架的電氣介面規格"

❌ **不好的問題**：
- "飛機怎麼飛？"（太籠統）
- "最好的戰機是什麼？"（主觀問題）
- "幫我設計一架戰機"（超出系統能力）

### 關鍵字選擇

使用**技術術語**和**具體型號**：
- ✅ "升力係數 Cl"、"Mach 數"、"攻角 AOA"
- ✅ "F-16"、"F-35"、"Su-27"
- ✅ "推力向量"、"複合材料"、"雷達截面積 RCS"

### 來源驗證

系統提供的來源引用可用於：
1. **追溯原始文件**：查看完整上下文
2. **驗證數據正確性**：對照原始資料
3. **引用格式**：用於技術報告或論文

## 故障排除

### 問題：找不到相關文件

**可能原因**：
1. 資料庫中沒有該領域的文件
2. 關鍵字不夠精確
3. 文件尚未建立索引

**解決方法**：
```bash
# 檢查可用的設計領域
docker exec <container> psql -U postgres -c \
  "SELECT name FROM langchain_pg_collection;"

# 使用 --debug 查看路由過程
./query.sh "你的問題" --debug
```

### 問題：回答不夠精確

**優化方法**：
1. **增加檢索文件數量**：
   ```bash
   ./query.sh "問題" --top-k 15  # 預設 10
   ```

2. **使用更具體的問題**：
   - 之前："飛控系統的運作原理"
   - 改進："F-16 飛控系統中 pitch rate damper 的實作"

3. **指定設計領域**：
   ```bash
   ./query.sh "問題" --collection "航電系統"
   ```

## 環境變數設定

確保 `.env` 檔案包含以下設定：

```bash
# PostgreSQL 向量資料庫
PGVECTOR_URL=postgresql://postgres:password@localhost:5433/postgres

# Embedding API（用於文件向量化）
EMBED_API_BASE=https://your-api-endpoint/v1
EMBED_API_KEY=your-api-key
EMBED_MODEL_NAME=nvidia/nv-embed-v2

# Chat Model（用於 Agent 推理）
CHAT_MODEL_NAME=openai/gpt-oss-20b
```

## 整合到大型系統

如果你要將 DATCOM 助理整合到多代理系統：

```python
from rag_system.subgraph import create_rag_subgraph
from rag_system.config import RAGConfig

# 建立 DATCOM subgraph
datcom_agent = create_rag_subgraph(llm, RAGConfig.from_env())

# 加入 parent graph
parent_graph.add_node("datcom_expert", datcom_agent)
```

詳見：[docs/AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) - Subgraph 整合指南

## 支援的文件格式

- **文件**：PDF, DOCX, RTF, TXT, Markdown
- **程式碼**：`.ada`, `.c`, `.cpp`, `.py`, `.m` (MATLAB)
- **數據**：CSV, Excel (需轉換為 PDF)
- **圖表**：作為 PDF 頁面嵌入

## 系統限制

1. **歷史資料依賴**：僅能回答基於已索引文件的問題
2. **無法進行設計**：提供參考資料，不自動生成設計
3. **數據時效性**：依賴已有的歷史數據，無法提供最新資訊
4. **程式碼執行**：僅檢索程式碼，不執行或編譯

## 常見問題 FAQ

**Q: 可以上傳機密文件嗎？**
A: 系統部署在本地，數據不外傳。但請遵守貴單位的資料安全政策。

**Q: 如何刪除某個設計領域？**
A: 使用資料庫工具刪除對應的 collection。

**Q: 支援圖片和圖表嗎？**
A: 目前僅支援文字檢索。圖表需以 PDF 形式嵌入文件中。

**Q: 可以同時查詢多個設計領域嗎？**
A: 系統會自動選擇最相關的單一領域。如需跨領域，請分別提問。

## 技術支援

- **文件**：[docs/AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)
- **資料庫**：[docs/DB_SETUP.md](DB_SETUP.md)
- **索引建立**：[docs/BUILD_USAGE.md](BUILD_USAGE.md)

---

**版本**: v0.3.0-DATCOM
**最後更新**: 2025-10-02
**維護**: DATCOM Team
