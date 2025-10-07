# 專案結構說明

本文件說明 RAG System 的完整目錄結構與各檔案用途。

## 📂 專案樹狀圖

```
RAG/
├── 📄 README.md                    # 專案主要說明文件
├── 📄 README.zh-TW.md              # 繁體中文版說明
├── 📄 requirements.txt             # Python 依賴套件清單
├── 📄 .env.example                 # 環境變數範本
├── 📄 .gitignore                   # Git 忽略規則
│
├── 🐳 docker-compose.yaml          # Docker Compose 設定
├── 🐳 Dockerfile                   # Docker 映像檔定義
├── 🐳 docker/                      # Docker 相關檔案
│   ├── init.sql                    # 資料庫初始化腳本
│   └── pg_hba.conf                 # PostgreSQL 存取控制
│
├── 🔧 query.sh                     # 便捷查詢腳本
├── 🔧 build_all.sh                 # 批次建立索引腳本
│
├── 📚 docs/                        # 所有文件集中處
│   ├── AGENT_ARCHITECTURE.md       # ReAct Agent 架構詳解
│   ├── DB_SETUP.md                 # 資料庫設定指南
│   ├── BUILD_USAGE.md              # 索引建立使用說明
│   ├── DATCOM_USAGE.md             # DATCOM 整合說明
│   ├── AGENTS.md                   # Agent 設計說明
│   └── PROJECT_STRUCTURE.md        # 本文件
│
├── 🎯 examples/                    # 使用範例
│   └── parent_agent.py             # 多代理系統整合範例
│
├── 💾 data/                        # 資料目錄（不納入版控）
│   ├── input/                      # 待處理的原始文件
│   ├── output/                     # 處理完成的輸出檔案
│   └── processed/                  # 中間處理結果
│
└── 🐍 rag_system/                  # 核心程式碼模組
    ├── __init__.py                 # 套件初始化
    ├── query_rag_pg.py             # CLI 查詢入口
    ├── agent.py                    # LangGraph workflow 編排
    ├── node.py                     # ReAct agent node 實現
    ├── state.py                    # State schema 定義
    ├── common.py                   # 共用工具函數
    ├── config.py                   # 配置管理
    ├── subgraph.py                 # Subgraph 包裝層
    │
    ├── tool/                       # Agent 工具模組
    │   ├── __init__.py
    │   ├── router.py               # Collection 路由工具
    │   ├── retrieve.py             # 向量檢索工具
    │   ├── article_lookup.py       # 條文精確查詢
    │   ├── metadata_search.py      # Metadata 搜尋工具
    │   └── shared.py               # 工具共用邏輯
    │
    └── build/                      # 索引建立工具
        ├── __init__.py
        ├── indexer.py              # 主要索引建立程式
        ├── document_parser.py      # 文件解析器
        ├── chunking.py             # 文件切塊邏輯
        ├── preprocess.py           # 文字前處理
        ├── structure_detector.py   # 文件結構偵測
        ├── db_utils.py             # 資料庫操作工具
        └── export.py               # 匯出功能
```

## 📝 目錄用途說明

### 根目錄檔案

| 檔案 | 用途 | 重要性 |
|------|------|--------|
| `README.md` | 專案主要說明，快速開始指南 | ⭐⭐⭐ |
| `requirements.txt` | Python 依賴套件清單 | ⭐⭐⭐ |
| `.env.example` | 環境變數範本，複製為 `.env` 使用 | ⭐⭐⭐ |
| `docker-compose.yaml` | Docker 服務編排（PostgreSQL + PGVector） | ⭐⭐⭐ |
| `query.sh` | 便捷查詢腳本，快速測試 RAG 系統 | ⭐⭐ |
| `build_all.sh` | 批次建立索引的腳本 | ⭐⭐ |

### 📚 `docs/` - 文件目錄

所有專案文件集中於此，便於查閱和維護。

| 文件 | 內容 |
|------|------|
| `AGENT_ARCHITECTURE.md` | **核心文件** - ReAct Agent 詳細架構、Subgraph 整合指南 |
| `DB_SETUP.md` | 資料庫設定、PGVector 安裝、Collection 管理 |
| `BUILD_USAGE.md` | 如何建立索引、文件處理流程 |
| `DATCOM_USAGE.md` | DATCOM 整合說明、UAV 戰機設計應用 |
| `AGENTS.md` | Agent 設計理念與實作細節 |
| `PROJECT_STRUCTURE.md` | 本文件 - 專案結構總覽 |

### 🎯 `examples/` - 範例程式

| 範例 | 說明 |
|------|------|
| `parent_agent.py` | **重要範例** - 展示如何將 RAG agent 整合到多代理系統 |

### 💾 `data/` - 資料目錄

**注意**: 此目錄不納入版控（`.gitignore` 已設定）

| 子目錄 | 用途 |
|--------|------|
| `input/` | 放置待處理的原始文件（PDF、DOCX 等） |
| `output/` | 存放處理完成的輸出檔案 |
| `processed/` | 存放中間處理結果（如切塊後的文字） |

### 🐍 `rag_system/` - 核心程式碼

#### 主要模組

| 檔案 | 職責 |
|------|------|
| `query_rag_pg.py` | **CLI 入口** - 處理命令列參數、執行查詢 |
| `agent.py` | **Workflow 編排** - 建構 LangGraph StateGraph |
| `node.py` | **Agent 實現** - ReAct agent node 邏輯 |
| `state.py` | **State 定義** - GraphState schema（MessagesState） |
| `subgraph.py` | **Subgraph 包裝** - 提供 parent graph 整合介面 |
| `config.py` | **配置管理** - RAGConfig 類別與參數驗證 |
| `common.py` | **共用工具** - 日誌、Embedding 模型等 |

#### `tool/` - Agent 工具

| 檔案 | 功能 |
|------|------|
| `router.py` | 智慧路由 - 判斷使用哪個 collection |
| `retrieve.py` | 向量檢索 - 語義相似度搜尋 |
| `article_lookup.py` | 條文查詢 - metadata filtering 精確匹配 |
| `metadata_search.py` | Metadata 搜尋工具 |
| `shared.py` | 工具共用邏輯（如建立 vectorstore） |

#### `build/` - 索引建立工具

| 檔案 | 功能 |
|------|------|
| `indexer.py` | **主程式** - 協調整個索引建立流程 |
| `document_parser.py` | 文件解析 - 支援 PDF、DOCX、RTF、TXT、MD |
| `chunking.py` | 文件切塊 - law/paragraph/smart 三種策略 |
| `preprocess.py` | 文字前處理 - 正規化、清理 |
| `structure_detector.py` | 結構偵測 - 識別「第X條」等法規結構 |
| `db_utils.py` | 資料庫操作 - Collection 管理 |
| `export.py` | 匯出功能 - 將處理結果匯出 |

## 🔧 常用操作路徑

### 1. 快速查詢

```bash
# 使用便捷腳本
./query.sh "陸海空軍懲罰法第24條"

# 或直接調用
python -m rag_system.query_rag_pg -q "你的問題"
```

### 2. 建立索引

```bash
# 批次建立
./build_all.sh

# 單一文件
python -m rag_system.build.indexer \
  --file data/input/法規.pdf \
  --collection "collection_name"
```

### 3. 啟動資料庫

```bash
# 使用 Docker Compose
docker-compose up -d

# 檢查狀態
docker-compose ps
```

### 4. 整合到大型系統

```python
# 參考 examples/parent_agent.py
from rag_system.subgraph import create_rag_subgraph
from rag_system.config import RAGConfig

rag_subgraph = create_rag_subgraph(llm, RAGConfig.from_env())
parent_graph.add_node("rag_agent", rag_subgraph)
```

## 📖 文件閱讀順序建議

### 新手入門
1. `README.md` - 了解專案概覽
2. `docs/DB_SETUP.md` - 設定資料庫
3. `docs/BUILD_USAGE.md` - 建立第一個索引
4. 執行 `./query.sh` 測試查詢

### Agent 開發者
1. `docs/AGENT_ARCHITECTURE.md` - 理解 ReAct 架構
2. `rag_system/node.py` - 看 agent 實作
3. `rag_system/tool/` - 了解工具機制
4. `examples/parent_agent.py` - 整合範例

### Subgraph 整合
1. `docs/AGENT_ARCHITECTURE.md` - 第 411 行起的「Subgraph 整合指南」
2. `rag_system/subgraph.py` - Subgraph API
3. `examples/parent_agent.py` - 完整範例
4. 執行範例測試整合

### 進階自訂
1. `docs/AGENTS.md` - Agent 設計理念
2. `rag_system/build/` - 客製化文件處理
3. `rag_system/config.py` - 配置選項
4. `docs/DATCOM_USAGE.md` - DATCOM 整合與 UAV 應用

## 🔄 資料流程圖

### 索引建立流程

```
data/input/文件.pdf
    ↓
document_parser.py (解析)
    ↓
preprocess.py (清理)
    ↓
structure_detector.py (結構分析)
    ↓
chunking.py (切塊)
    ↓
indexer.py (向量化 + 儲存)
    ↓
PostgreSQL + PGVector
```

### 查詢流程

```
使用者問題
    ↓
query_rag_pg.py (CLI 入口)
    ↓
agent.py (啟動 StateGraph)
    ↓
node.py (ReAct agent)
    ↓
tool/router.py (選擇 collection)
    ↓
tool/retrieve.py (向量檢索)
    ↓
node.py (評估 + 生成答案)
    ↓
返回結果
```

## 🚀 維護建議

### 定期檢查

- [ ] 檢查 `data/` 目錄大小，定期清理舊檔案
- [ ] 更新 `requirements.txt` 時同步更新 `README.md`
- [ ] 新增功能時更新對應的 `docs/` 文件
- [ ] 保持 `.env.example` 與實際需求同步

### 文件更新

- 新增 tool → 更新 `docs/AGENT_ARCHITECTURE.md`
- 修改 state → 更新 `docs/AGENT_ARCHITECTURE.md` + `state.py` docstring
- 新增範例 → 放在 `examples/` 並在 `README.md` 提及
- 架構變更 → 更新本文件 `PROJECT_STRUCTURE.md`

## 📞 尋求幫助

遇到問題時的查找順序：

1. **README.md** - 快速開始和常見問題
2. **docs/AGENT_ARCHITECTURE.md** - Agent 相關問題
3. **docs/DB_SETUP.md** - 資料庫問題
4. **docs/BUILD_USAGE.md** - 索引建立問題
5. **examples/** - 查看實際範例
6. **原始碼註解** - 詳細實作細節

---

**版本**: v0.3.0
**最後更新**: 2025-10-02
**維護者**: RAG System Team
