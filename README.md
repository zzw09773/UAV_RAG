# RAG System with ReAct Agent

一個基於 **ReAct Agent** 架構的智能檢索增強生成（RAG）系統，專門針對繁體中文法規文件優化。系統使用單一 agent node 架構，透過 LangGraph 與 LangChain 實現自主檢索、評估與答案生成。

---

## ✨ 核心特性

### 🤖 ReAct Agent 架構
- **單一 Node 設計**：整個 workflow 只有一個 ReAct agent node
- **自主決策**：LLM 自動決定何時檢索、何時重寫查詢、何時生成答案
- **工具調用**：透過 LangChain Tools 進行文件檢索與處理
- **LangGraph 編排**：使用 StateGraph 管理狀態與流程

### 📚 文件處理能力
- **多格式支援**：PDF、DOCX、RTF、TXT、Markdown
- **智能切塊**：
  - `law` 策略：針對「第X條」結構優化
  - `paragraph` 策略：通用段落切分
  - `smart` 策略：LLM 輔助智能切分
- **向量化儲存**：PostgreSQL + PGVector 高效語意搜尋

### 🗄️ 向量資料庫
- **PGVector**：PostgreSQL 原生向量擴展
- **Collection 管理**：支援多個文件集合
- **批次處理**：高效索引建立流程
- **Docker 部署**：一鍵啟動資料庫環境

---

## 🏗️ 系統架構

```
RAG/
├── 📄 README.md                 # 專案說明（本文件）
├── 📄 requirements.txt          # Python 依賴套件
├── 📄 .env.example              # 環境變數範本
├── 🐳 docker-compose.yaml       # Docker 服務編排
├── 🔧 query.sh                  # 便捷查詢腳本
│
├── 📚 docs/                     # 文件目錄
│   ├── AGENT_ARCHITECTURE.md    # ReAct Agent 架構 + Subgraph 指南
│   ├── DB_SETUP.md              # 資料庫設定指南
│   ├── BUILD_USAGE.md           # 索引建立使用說明
│   └── PROJECT_STRUCTURE.md     # 完整專案結構說明
│
├── 🎯 examples/                 # 範例程式
│   └── parent_agent.py          # 多代理系統整合範例
│
├── 💾 data/                     # 資料目錄（不納入版控）
│   ├── input/                   # 待處理文件
│   ├── output/                  # 輸出結果
│   └── processed/               # 中間檔案
│
└── 🐍 rag_system/               # 核心程式碼
    ├── query_rag_pg.py          # CLI 入口點
    ├── agent.py                 # LangGraph workflow 編排
    ├── node.py                  # ReAct agent node 實現
    ├── state.py                 # GraphState 狀態定義（MessagesState）
    ├── subgraph.py              # Subgraph 包裝層
    ├── config.py                # 配置管理
    ├── common.py                # 共用工具函數
    │
    ├── tool/                    # Agent 工具模組
    │   ├── router.py            # Collection 路由
    │   ├── retrieve.py          # 向量檢索
    │   ├── article_lookup.py    # 條文精確查詢
    │   └── metadata_search.py   # Metadata 搜尋
    │
    └── build/                   # 索引建立工具
        ├── indexer.py           # 主要索引程式
        ├── document_parser.py   # 文件解析器
        └── chunking.py          # 文本切塊邏輯
```

> 📖 **完整專案結構說明**: 請參考 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

### v0.3.0 新增功能 🎉

- ✨ **Subgraph 模式** - 可作為大型多代理系統的專業節點
- ✨ **MessagesState 架構** - 與 LangGraph 完全相容
- ✨ **範例程式** - 多代理協同系統展示
- 📚 **文件整理** - 所有文件集中於 `docs/` 目錄

### 整合到大型系統

如果你想將此 RAG agent 整合到大型多代理系統：

```python
from rag_system.subgraph import create_rag_subgraph
from rag_system.config import RAGConfig

# 建立 RAG subgraph
rag_node = create_rag_subgraph(llm, RAGConfig.from_env())

# 加入你的 parent graph
parent_graph.add_node("legal_expert", rag_node)
```

詳細指南請參考: [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) 第 411 行起的「Subgraph 整合指南」

---

## 🚀 快速開始

### 1. 環境需求

- Python 3.9+
- Docker & Docker Compose（資料庫）
- 8GB+ RAM（建議）

### 2. 安裝依賴

```bash
# 克隆專案
git clone <your-repo-url>
cd RAG

# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安裝套件
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
# 複製範本
cp .env.example .env

# 編輯 .env，填入你的 API 設定
nano .env
```

**必要設定**：
```bash
PGVECTOR_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/postgres"
EMBED_API_KEY=your_embedding_api_key
EMBED_API_BASE=http://your-api-server/v1
EMBED_MODEL_NAME=nvidia/nv-embed-v2
CHAT_MODEL_NAME=openai/gpt-oss-20b
```

### 4. 啟動資料庫

```bash
cd rag_system
docker compose up -d pgvector
```

驗證資料庫狀態：
```bash
docker compose ps
# 應該看到 rag_db 容器處於 Up (healthy) 狀態
```

**詳細資料庫設定請參考 [docs/DB_SETUP.md](docs/DB_SETUP.md)**

---

## 📖 使用方式

### 建立索引

將文件放入 `rag_system/documents/` 目錄，然後執行：

```bash
cd rag_system

# 基本用法
python -m build.indexer \
  --input_dir ./documents \
  --collection my_laws \
  --split law

# 為每個子目錄建立獨立 collection
python -m build.indexer \
  --input_dir ./documents \
  --collection laws \
  --split law \
  --per_dir

# 重置並重建 collection
python -m build.indexer \
  --input_dir ./documents \
  --collection my_laws \
  --split law \
  --reset_collection
```

**切塊策略**：
- `law`：針對法規文件（偵測「第X條」結構）
- `paragraph`：通用段落切分
- `smart`：使用 LLM 智能切分（需配置 LLM_API_KEY）

### 查詢系統

#### 單次查詢

```bash
python -m rag_system.query_rag_pg \
  -q "著作權法第五條的規定內容" \
  --collection my_laws
```

#### 互動模式

```bash
python -m rag_system.query_rag_pg --collection my_laws

# 進入互動模式後
> 什麼是合理使用？
> 著作權保護期限是多久？
> exit  # 或按 Ctrl+C 離開
```

#### 除錯模式

```bash
python -m rag_system.query_rag_pg \
  -q "你的問題" \
  --collection my_laws \
  --debug
```

除錯模式會顯示：
- Agent 推理過程（Thought-Action-Observation）
- 檢索到的文件內容
- 中間決策步驟

#### 僅檢索（不生成答案）

```bash
python -m rag_system.query_rag_pg \
  -q "關鍵字" \
  --collection my_laws \
  --retrieve-only > results.json
```

---

## 🔧 進階配置

### CLI 參數完整列表

```bash
python -m rag_system.query_rag_pg --help
```

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--conn` | PostgreSQL 連接字串 | 從 `.env` 讀取 |
| `--collection` | Collection 名稱 | **必需** |
| `--embed_model` | 嵌入模型名稱 | `nvidia/nv-embed-v2` |
| `--chat_model` | 對話模型名稱 | `openai/gpt-oss-20b` |
| `--embed_api_base` | 嵌入 API 端點 | 從 `.env` 讀取 |
| `--embed_api_key` | API 金鑰 | 從 `.env` 讀取 |
| `--no-verify-ssl` | 停用 SSL 驗證 | `False` |
| `-q, --query` | 查詢問題 | 無（進入互動模式） |
| `--retrieve-only` | 僅檢索文件 | `False` |
| `--debug` | 除錯模式 | `False` |

### 自訂 System Prompt

編輯 `rag_system/node.py` 中的 `SYSTEM_PROMPT` 變數：

```python
SYSTEM_PROMPT = """你是一個專門處理繁體中文法規文件的法律問答助理。

你的任務是：
1. 使用 retrieve_legal_documents 工具來搜尋相關的法規文件
2. 仔細閱讀檢索到的文件內容
3. 根據文件內容提供簡潔、準確的答案（最多 3 句話）
4. **必須**在答案後附上來源引用
...
"""
```

### 新增自訂工具

1. 在 `rag_system/tool/` 建立新工具檔案：

```python
# tool/custom_tool.py
from langchain.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Tool description for the LLM."""
    # 實作邏輯
    return result
```

2. 在 `query_rag_pg.py` 的 `build_graph()` 中加入：

```python
from .tool.custom_tool import my_custom_tool

tools = [retrieve_tool, my_custom_tool]
```

---

## 🧪 測試與驗證

### 基本功能測試

```bash
# 1. 測試資料庫連接
docker exec -it rag_db psql -U postgres -c "SELECT 1;"

# 2. 測試 CLI 參數
python -m rag_system.query_rag_pg --help

# 3. 測試檢索（需先建立索引）
python -m rag_system.query_rag_pg \
  -q "測試查詢" \
  --collection your_collection \
  --retrieve-only
```

### 系統架構驗證

參考 `rag_system/REACT_AGENT_README.md` 了解詳細架構設計。

---

## 📊 效能與限制

### Token 消耗

ReAct Agent 使用多輪推理（Thought-Action-Observation），token 消耗比傳統 RAG 高：

- 簡單查詢：~1,500-3,000 tokens
- 複雜查詢（多次檢索）：~3,000-6,000 tokens

### 系統限制

- **最大檢索數量**：10 documents/query
- **文件截斷長度**：800 字元/document（可調整）
- **LangGraph 遞迴限制**：預設 20 層（可調整）

### 最佳實踐

1. **使用明確的查詢**：「著作權法第五條」比「著作權」更好
2. **Collection 命名**：使用描述性名稱（如 `copyright_laws`）
3. **批次索引**：一次建立完整 collection，避免頻繁增量更新
4. **監控 token 使用**：啟用 `--debug` 觀察 agent 行為

---

## 🔍 故障排除

### 問題 1：無法連接資料庫

**錯誤訊息**：
```
psycopg2.OperationalError: could not connect to server
```

**解決方法**：
1. 確認資料庫已啟動：`docker compose ps`
2. 檢查連接埠：預設 5433，確認 `.env` 設定正確
3. 驗證連接：`docker exec -it rag_db psql -U postgres`

詳細排查請參考 [docs/DB_SETUP.md](docs/DB_SETUP.md)。

### 問題 2：找不到 collection

**錯誤訊息**：
```
Collection 'xxx' not found
```

**解決方法**：
1. 檢查 collection 是否存在：
   ```bash
   docker exec -it rag_db psql -U postgres -c \
     "SELECT name FROM langchain_pg_collection;"
   ```
2. 確認 `--collection` 參數拼寫正確
3. 如使用 `--per_dir`，collection 名稱格式為 `{collection}_{subdir}`

### 問題 3：API 錯誤

**錯誤訊息**：
```
httpx.HTTPStatusError: 401 Unauthorized
```

**解決方法**：
1. 檢查 `.env` 中的 API 金鑰是否正確
2. 驗證 API 端點可連接：`curl $EMBED_API_BASE`
3. 確認模型名稱正確（如 `nvidia/nv-embed-v2`）

---

## 🛠️ 開發指南

### 專案結構說明

- **`rag_system/query_rag_pg.py`**：CLI 入口，處理參數與應用邏輯
- **`rag_system/agent.py`**：LangGraph workflow 定義（只有 1 個 node）
- **`rag_system/node.py`**：ReAct agent node 實現，包含 system prompt
- **`rag_system/state.py`**：GraphState 定義（question, generation）
- **`rag_system/tool/retrieve.py`**：文件檢索工具實現

### 模組職責

| 模組 | 職責 |
|------|------|
| `build/` | 文件解析、切塊、向量化、索引建立 |
| `tool/` | Agent 可調用的工具（檢索、API 調用等） |
| `node.py` | Agent 推理邏輯與 system prompt |
| `agent.py` | Workflow 編排（entry → agent → end） |
| `query_rag_pg.py` | CLI 與應用程式進入點 |

### 貢獻指南

1. Fork 專案
2. 建立 feature branch：`git checkout -b feature/your-feature`
3. 提交變更：`git commit -m "Add your feature"`
4. 推送到 branch：`git push origin feature/your-feature`
5. 建立 Pull Request

---

## 📚 技術棧

### 核心框架
- **LangChain** (0.3+)：LLM 整合框架
- **LangGraph** (0.2+)：Agent workflow 編排
- **LangChain OpenAI**：Chat model 整合

### 資料庫與向量儲存
- **PostgreSQL** (17+)：關聯式資料庫
- **PGVector** (0.8+)：向量擴展
- **psycopg2**：Python PostgreSQL 驅動

### 文件處理
- **PyMuPDF**：PDF 解析
- **python-docx**：DOCX 解析
- **striprtf**：RTF 解析

### 工具與套件
- **httpx**：HTTP 客戶端
- **tiktoken**：Token 計數
- **orjson**：高效 JSON 處理
- **python-dotenv**：環境變數管理

---

## 📄 授權

[請根據實際情況添加授權資訊]

---

## 🙏 致謝

本專案基於以下開源專案：
- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [PGVector](https://github.com/pgvector/pgvector)

參考架構：
- [ai-innovation-AI-Agent](https://github.com/your-reference/ai-innovation-AI-Agent)

---

## 📞 聯絡與支援

- **Issues**：[GitHub Issues](your-repo-url/issues)
- **文件**：[專案文件](your-docs-url)

---

## 🗺️ Roadmap

- [ ] 支援串流輸出（Streaming）
- [ ] Web API 介面（FastAPI）
- [ ] 多模態文件支援（圖片、表格）
- [ ] 混合檢索（BM25 + Vector）
- [ ] 查詢緩存機制
- [ ] 效能監控面板

---

**最後更新**：2025-09-30