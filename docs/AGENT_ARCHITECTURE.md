# ReAct Agent 架構文件

## 系統概述

基於 LangGraph 的 ReAct Agent 實現，專為繁體中文法規文件檢索與問答設計。支援智慧路由、向量檢索、條文精確查詢等功能。

**v0.3.0 起支援 Subgraph 模式** - 可作為大型多代理系統的專業節點。

## 快速開始 - 大 Agent 整合

如果你想將此 RAG agent 整合到你的大型多代理系統中，請跳至 [Subgraph 整合指南](#subgraph-整合指南---大-agent-使用說明)。

## 架構設計

### 目錄結構

```
rag_system/
├── query_rag_pg.py           # CLI 入口點與應用主邏輯
├── agent.py                  # LangGraph workflow 編排
├── node.py                   # ReAct agent node 實現
├── state.py                  # GraphState 狀態定義（MessagesState）
├── subgraph.py               # Subgraph 包裝層（NEW）
├── tool/                     # Agent 工具模組
│   ├── __init__.py
│   ├── router.py             # Collection 路由工具
│   ├── retrieve.py           # 向量檢索工具
│   ├── article_lookup.py     # 條文編號精確查詢工具
│   ├── metadata_search.py    # Metadata 搜尋工具
│   └── shared.py             # 共享工具函數
└── common.py                 # 共享邏輯與嵌入模型

examples/
└── parent_agent.py           # 多代理系統整合範例（NEW）
```

### 核心架構

**Standalone Mode（獨立模式）**：
```
Entry → agent_node (ReAct循環) → END
```

**Subgraph Mode（子圖模式）**：
```
Parent Graph → Router → RAG Agent (subgraph) → Coordinator → END
```

所有邏輯（路由、檢索、條文查詢、評估、生成）皆由 ReAct agent 透過工具調用與推理完成。

### 模組職責

#### `state.py` - 狀態管理
```python
class GraphState(TypedDict):
    question: str      # 用戶查詢
    generation: str    # 生成的答案
```

#### `tool/router.py` - Collection 路由
- 智慧路由功能，根據問題內容判斷應使用哪個 collection
- 使用 LLM 進行語義理解和分類

#### `tool/retrieve.py` - 向量檢索
- 基於語義相似度的文件檢索
- 適用於一般性問題和內容關鍵字查詢

#### `tool/article_lookup.py` - 條文精確查詢（新增）
- **解決問題**：向量檢索無法有效匹配條文編號（如「第24條」）
- **實現方式**：使用 metadata filtering 進行精確匹配
- **支援格式**：
  - 中文：`第24條`、`第 24 條`
  - 英文：`article 24`、`art. 24`
- **查詢流程**：
  1. Regex 提取條文編號
  2. SQL WHERE 過濾 metadata
  3. 返回完整條文內容

#### `node.py` - Agent Node
- 定義 `SYSTEM_PROMPT`：agent 行為指令
- `create_agent_node()`：建立 ReAct agent
- 整合 LLM 與工具調用邏輯

#### `agent.py` - Workflow 編排
- `build_workflow()`：建構 LangGraph workflow
- 極簡設計：單一 node + 單一 edge

#### `query_rag_pg.py` - 應用入口
- CLI 參數解析
- `RagApplication` 類別封裝應用邏輯
- 支援互動模式與單次查詢

## 使用方式

### 便捷腳本

```bash
# 基本查詢
./query.sh "螺旋槳推力係數如何計算？"

# 條文查詢（使用新功能）
./query.sh "陸海空軍懲罰法第24條"

# 指定 collection
./query.sh "申誡的規定" --collection "陸海空軍懲罰法"

# 除錯模式
./query.sh "測試問題" --debug
```

### 直接調用

```bash
# 單次查詢
python -m rag_system.query_rag_pg -q "著作權法第五條"

# 互動模式
python -m rag_system.query_rag_pg

# 僅檢索（JSON 輸出）
python -m rag_system.query_rag_pg \
  -q "關鍵字" \
  --collection "collection_name" \
  --retrieve-only
```

## CLI 參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--conn` | PostgreSQL 連接字串 | `$PGVECTOR_URL` |
| `--collection` | 強制指定 collection（繞過路由） | None |
| `--embed_model` | 嵌入模型名稱 | `nvidia/nv-embed-v2` |
| `--chat_model` | 聊天模型名稱 | `openai/gpt-oss-20b` |
| `--embed_api_base` | API base URL | `$EMBED_API_BASE` |
| `--embed_api_key` | API key | `$EMBED_API_KEY` |
| `--no-verify-ssl` | 停用 SSL 驗證 | False |
| `-q, --query` | 查詢問題 | None（進入互動模式） |
| `--retrieve-only` | 只檢索不生成答案 | False |
| `--debug` | 顯示詳細日誌 | False |

## Agent 工作流程

### 一般查詢流程

1. **路由判斷** → 使用 `collection_router` 工具判斷應使用哪個 collection
2. **檢索文件** → 使用 `retrieve_legal_documents` 工具進行向量檢索
3. **評估相關性** → LLM 評估檢索結果是否相關
4. **決策分支**：
   - ✅ 相關 → 生成答案
   - ❌ 不相關 → 改寫問題，重新檢索
   - 🔄 多次失敗 → 誠實告知無法找到
5. **生成答案** → 提供簡潔答案並附上來源引用
6. **更新狀態** → 回傳結果至 `state['generation']`

### 條文查詢流程（新增）

1. **條文識別** → LLM 識別查詢中包含條文編號
2. **精確查詢** → 使用 `lookup_article_by_number` 工具
3. **Metadata 過濾** → 直接從資料庫 metadata 精確匹配條文
4. **返回結果** → 完整條文內容 + 來源
5. **生成答案** → 基於條文內容回答問題

### 工具選擇邏輯

Agent 會根據問題類型自動選擇最佳工具：

| 問題類型 | 使用工具 | 範例 |
|---------|---------|------|
| 不確定 collection | `collection_router` | "軍人申誡的規定" |
| 一般語義查詢 | `retrieve_legal_documents` | "無人機飛行限制" |
| 條文編號查詢 | `lookup_article_by_number` | "陸海空軍懲罰法第24條" |

## 系統提示（SYSTEM_PROMPT）

```
你是一個專門處理繁體中文法規文件的法律問答助理。

你有以下工具可用：
1. collection_router - 判斷問題應使用哪個文件庫
2. retrieve_legal_documents - 使用向量檢索搜尋相關文件
3. lookup_article_by_number - 精確查詢特定條文編號

你的任務：
1. 分析問題，選擇適當的工具
2. 如果問題包含條文編號（如「第24條」），優先使用 lookup_article_by_number
3. 仔細閱讀檢索到的文件內容
4. 提供簡潔、準確的答案（最多 3 句話）
5. **必須**附上來源引用：(來源: 檔案名, 頁碼)

重要規則：
- 條文編號查詢使用 lookup_article_by_number
- 一般問題使用 retrieve_legal_documents
- 檢索結果不相關時，改寫問題再試
- 多次失敗後，誠實告知找不到
- 答案必須基於檢索到的文件
```

## 技術細節

### Hybrid Search 實現

**問題背景**：
- 向量檢索依賴**語義相似度**
- 結構化標識符（如「第24條」）相似度計算效果差
- 導致無法精確匹配條文編號

**解決方案**：
1. **向量檢索**（retrieve.py）
   - 適用：內容關鍵字、語義查詢
   - 實現：`PGVector.similarity_search()`

2. **Metadata Filtering**（article_lookup.py）
   - 適用：條文編號精確匹配
   - 實現：SQL WHERE 條件過濾
   - 查詢範例：
   ```sql
   SELECT document, cmetadata
   FROM langchain_pg_embedding
   WHERE collection_id = :collection_id
     AND cmetadata->>'article' = '第 24 條'
   ```

### Regex 條文識別

支援多種條文編號格式：
```python
patterns = [
    r'第\s*(\d+)\s*條',  # 第24條, 第 24 條
    r'article\s*(\d+)',  # article 24
    r'art\.\s*(\d+)',    # art. 24
]
```

### 錯誤處理

1. **條文不存在** → 提示找不到該條文
2. **Regex 無法識別** → 降級使用向量檢索
3. **資料庫連線失敗** → 返回錯誤訊息
4. **SSL 憑證問題** → 使用 `--no-verify-ssl` flag

## 擴展指南

### 新增工具

1. 建立工具檔案 `tool/my_tool.py`：
```python
from langchain.tools import tool
from ..common import log

def create_my_tool(config_param: str) -> Callable:
    @tool
    def my_tool(input: str) -> str:
        """工具描述（LLM 會讀取）。

        Args:
            input: 輸入說明

        Returns:
            輸出說明
        """
        log(f"Executing my_tool with: {input}")
        # 實作邏輯
        return "result"

    return my_tool
```

2. 註冊到 `tool/__init__.py`：
```python
from .my_tool import create_my_tool

__all__ = [..., "create_my_tool"]
```

3. 整合到 `query_rag_pg.py`：
```python
from .tool import ..., create_my_tool

def build_graph(self):
    my_tool = create_my_tool(config_param="value")
    tools = [router_tool, retrieve_tool, article_lookup_tool, my_tool]
    ...
```

### 調整系統提示

修改 `node.py` 的 `SYSTEM_PROMPT`：
```python
SYSTEM_PROMPT = """
你是一個...
（添加新指令）
"""
```

### 修改狀態結構

如需新增狀態欄位，修改 `state.py`：
```python
class GraphState(TypedDict):
    question: str
    generation: str
    context: list[str]  # 新增
    metadata: dict       # 新增
```

## 測試

### 基本測試

```bash
# 幫助訊息
./query.sh --help

# 資料庫連線測試
docker exec 2e79fa1aabce psql -U postgres -c "SELECT 1;"

# API 連線測試
curl -k https://172.16.120.67/v1/models
```

### 功能測試

```bash
# 向量檢索測試
./query.sh "申誡的規定"

# 條文查詢測試
./query.sh "陸海空軍懲罰法第24條"

# 路由功能測試
./query.sh "螺旋槳推力計算"

# Collection 指定測試
./query.sh "測試問題" --collection "collection_name"
```

### 除錯模式

```bash
# 啟用詳細日誌
./query.sh "測試問題" --debug

# 檢視 LLM 推理過程
# 觀察 agent 的 thought-action-observation 循環
```

## 效能考量

### Token 消耗

- **ReAct 循環**：每次循環消耗 thought + action + observation tokens
- **預期**：單次查詢 2-5 輪循環
- **優化**：精簡系統提示、限制檢索文件數量

### 查詢延遲

| 操作 | 預期延遲 | 優化方式 |
|------|---------|---------|
| 路由判斷 | ~1-2s | LLM 推理時間 |
| 向量檢索 | ~0.5-1s | PGVector 索引 |
| 條文查詢 | ~0.1-0.3s | SQL metadata 過濾 |
| 答案生成 | ~2-4s | LLM 生成時間 |
| **總計** | **~4-8s** | - |

### 快取策略

- Vectorstore 實例在工具內重複使用
- Embeddings 透過 PGVector 快取
- 條文查詢使用資料庫索引加速

## 已知限制

1. **LLM 依賴**：需要穩定的 LLM API 服務
2. **遞迴深度**：預設 recursion_limit，需要時可調整
3. **並發處理**：單執行緒設計，不支援並發查詢
4. **條文格式**：依賴特定的 metadata 結構（`cmetadata->>'article'`）

## 故障排除

### 問題：Connection error
- **原因**：SSL 憑證驗證失敗
- **解決**：使用 `--no-verify-ssl` 或修正憑證

### 問題：條文查詢失敗
- **原因**：metadata 中條文格式不符
- **檢查**：
  ```sql
  SELECT DISTINCT cmetadata->>'article'
  FROM langchain_pg_embedding
  WHERE collection_id = '...';
  ```

### 問題：找不到相關文件
- **原因**：collection 為空或查詢關鍵字不匹配
- **檢查**：
  ```bash
  ./query.sh "測試" --retrieve-only --collection "collection_name"
  ```

### 問題：PostgreSQL 連線失敗
- **原因**：容器未啟動
- **解決**：
  ```bash
  docker compose up -d
  docker compose ps
  ```

---

# Subgraph 整合指南 - 大 Agent 使用說明

## 目錄

- [為什麼使用 Subgraph](#為什麼使用-subgraph)
- [前置需求](#前置需求)
- [快速整合 5 步驟](#快速整合-5-步驟)
- [完整範例](#完整範例)
- [State 管理](#state-管理)
- [進階應用](#進階應用-1)
- [常見問題](#常見問題)

---

## 為什麼使用 Subgraph

如果你正在建構一個大型多代理系統，需要：
- ✅ 將法律文件問答作為其中一個專業能力
- ✅ 與其他 agent（天氣、計算、知識庫等）協同工作
- ✅ 統一管理對話歷史和狀態
- ✅ 動態路由到不同的專業 agent

那麼你應該使用 **Subgraph 模式**。

### 架構對比

**❌ 錯誤方式 - 直接調用**
```python
# 問題：無法與其他 agent 共享 state
rag_answer = rag_standalone.invoke({"question": q})
weather_answer = weather_agent.invoke({"query": q})
# 難以協調、無統一 state
```

**✅ 正確方式 - Subgraph 整合**
```python
# 所有 agent 共享 MessagesState，統一編排
parent_graph.add_node("rag_agent", rag_subgraph)
parent_graph.add_node("weather_agent", weather_subgraph)
parent_graph.add_conditional_edges("router", route_to_agent)
```

---

## 前置需求

### 1. 環境變數設定

確保以下環境變數已設定（`.env` 檔案）：

```bash
# PostgreSQL 向量資料庫
PGVECTOR_URL=postgresql://user:password@host:port/database

# Embedding API
EMBED_API_BASE=https://your-api-endpoint/v1
EMBED_API_KEY=your-api-key
EMBED_MODEL_NAME=nvidia/nv-embed-v2

# Chat Model
CHAT_MODEL_NAME=openai/gpt-oss-20b
```

### 2. 安裝依賴

```bash
pip install langgraph langchain-openai langchain-postgres python-dotenv httpx
```

### 3. 資料庫準備

確保 PostgreSQL 有至少一個 collection 包含法律文件。

---

## 快速整合 5 步驟

### 步驟 1: 引入必要模組

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, END
from langchain_core.messages import HumanMessage

# 引入 RAG subgraph
from rag_system.config import RAGConfig
from rag_system.subgraph import create_rag_subgraph
```

### 步驟 2: 建立 LLM 和配置

```python
import httpx
from dotenv import load_dotenv

load_dotenv()

# RAG 配置（自動從環境變數讀取）
rag_config = RAGConfig.from_env()
rag_config.validate()  # 驗證配置完整性

# 建立 LLM（與 RAG 共用）
client = httpx.Client(
    verify=rag_config.verify_ssl,
    follow_redirects=True,
    timeout=httpx.Timeout(120.0, connect=10.0)
)
llm = ChatOpenAI(
    model=rag_config.chat_model,
    openai_api_key=rag_config.embed_api_key,
    openai_api_base=rag_config.embed_api_base,
    temperature=0,
    http_client=client
)
```

### 步驟 3: 建立 RAG Subgraph

```python
# 建立 RAG subgraph - 就這麼簡單！
rag_subgraph = create_rag_subgraph(
    llm=llm,
    config=rag_config,
    name="legal_expert"  # 給 subgraph 一個名稱
)
```

### 步驟 4: 整合到 Parent Graph

```python
# 建立 parent graph
parent_graph = StateGraph(MessagesState)

# 將 RAG subgraph 加為一個節點
parent_graph.add_node("rag_agent", rag_subgraph)

# 其他 agent（範例）
parent_graph.add_node("general_agent", your_other_agent)

# 設定路由邏輯
parent_graph.set_entry_point("rag_agent")  # 或使用 router
parent_graph.add_edge("rag_agent", END)

# 編譯
app = parent_graph.compile()
```

### 步驟 5: 執行查詢

```python
# 使用 MessagesState 格式輸入
result = app.invoke({
    "messages": [HumanMessage(content="陸海空軍懲罰法第24條是什麼？")]
})

# 取得回答
final_message = result['messages'][-1]
print(final_message.content)
```

**就這樣！** 🎉 你的大 Agent 現在已經整合了法律問答能力。

---

## 完整範例

### 情境：多專業 Agent 協同系統

你的系統需要處理多種問題類型：
- 法律問題 → RAG Agent
- 天氣查詢 → Weather Agent
- 數學計算 → Calculator Agent
- 一般對話 → General Agent

完整程式碼請參考 [examples/parent_agent.py](../examples/parent_agent.py)。

### 核心程式碼解析

```python
from langgraph.graph import StateGraph, MessagesState, END
from typing import Literal

# 1. 定義 Parent State（可選，也可直接用 MessagesState）
class ParentState(MessagesState):
    current_agent: str = ""  # 追蹤當前使用的 agent
    task_type: str = ""      # 任務類型

# 2. 建立 Router Node
def create_router_node(llm):
    def router_node(state: ParentState) -> dict:
        question = state['messages'][-1].content
        # 使用 LLM 判斷路由
        agent = decide_agent(question)  # 你的路由邏輯
        return {"current_agent": agent}
    return router_node

# 3. 建立 Parent Graph
def build_parent_graph(llm, rag_config):
    graph = StateGraph(ParentState)

    # 加入所有 agent nodes
    graph.add_node("router", create_router_node(llm))
    graph.add_node("rag_agent", create_rag_subgraph(llm, rag_config))
    graph.add_node("weather_agent", create_weather_agent())
    graph.add_node("calculator_agent", create_calculator_agent())

    # 設定 workflow
    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        lambda state: state["current_agent"],  # 根據 router 決定
        {
            "rag_agent": "rag_agent",
            "weather_agent": "weather_agent",
            "calculator_agent": "calculator_agent"
        }
    )

    # 所有 agent 回到 END
    graph.add_edge("rag_agent", END)
    graph.add_edge("weather_agent", END)
    graph.add_edge("calculator_agent", END)

    return graph.compile()

# 4. 執行
app = build_parent_graph(llm, rag_config)
result = app.invoke({
    "messages": [HumanMessage(content="陸海空軍懲罰法第24條")],
    "current_agent": "",
    "task_type": ""
})
```

### 執行完整範例

```bash
cd /home/c1147259/桌面/RAG
python examples/parent_agent.py
```

輸出範例：
```
[Router] Selected agent: rag_agent
[RAG Agent] Processing legal query...
[Response Formatter] Formatting final response...

Final Answer:
根據陸海空軍懲罰法第24條規定，申誡由權責主管以書面或言詞行之...
(來源: 陸海空軍懲罰法.pdf, p12)
```

---

## State 管理

### State 自動轉換

RAG subgraph 會自動處理兩種輸入模式：

**Parent Graph 傳入 (MessagesState)**：
```python
{
    "messages": [HumanMessage(content="第24條")],
    # RAG 自動從 messages 提取問題
}
```

**Standalone 模式 (向下相容)**：
```python
{
    "question": "第24條",
    "generation": ""
    # 傳統模式仍然支援
}
```

### State 欄位說明

RAG subgraph 使用的 `GraphState` 結構：

```python
class GraphState(MessagesState):
    # 繼承自 MessagesState
    messages: list  # 對話歷史（與 parent graph 共享）

    # RAG 專用欄位
    question: str = ""        # 用戶問題（向下相容）
    generation: str = ""      # 最終答案
    collection: str = ""      # 選中的 collection
    retrieved_docs: list = [] # 檢索到的文件
```

### State 更新機制

```python
# RAG agent 返回更新
return {
    "generation": "答案內容...",
    "messages": [AIMessage(content="答案內容...")]
}

# Parent graph 接收
# state['messages'] 被追加（add_messages reducer）
# state['generation'] 被更新
```

---

## 進階應用

### 1. 多個 RAG Subgraph（不同法域）

```python
# 台灣法律 RAG
tw_config = RAGConfig.from_env()
tw_rag = create_rag_subgraph(llm, tw_config, name="taiwan_law")

# 美國法律 RAG（不同資料庫）
us_config = RAGConfig(
    conn_string=os.getenv("US_PGVECTOR_URL"),
    embed_api_base=os.getenv("EMBED_API_BASE"),
    # ... 其他配置
)
us_rag = create_rag_subgraph(llm, us_config, name="us_law")

# 加入 parent graph
graph.add_node("taiwan_law_agent", tw_rag)
graph.add_node("us_law_agent", us_rag)

# 根據問題路由到不同法域
graph.add_conditional_edges(
    "router",
    route_by_jurisdiction,  # 判斷台灣法 vs 美國法
    {"taiwan": "taiwan_law_agent", "us": "us_law_agent"}
)
```

### 2. Streaming 串流輸出

```python
# 使用 stream 即時取得 agent 輸出
for chunk in app.stream(
    {"messages": [HumanMessage(content="第24條")]},
    stream_mode="values"
):
    if chunk.get('messages'):
        print(chunk['messages'][-1].content)
```

### 3. 加入 Checkpointer（對話記憶）

```python
from langgraph.checkpoint.memory import MemorySaver

# 加入記憶功能
memory = MemorySaver()
app = parent_graph.compile(checkpointer=memory)

# 使用 thread_id 維持對話
config = {"configurable": {"thread_id": "user_123"}}
result1 = app.invoke({"messages": [HumanMessage("第24條")]}, config)
result2 = app.invoke({"messages": [HumanMessage("那第25條呢？")]}, config)
# result2 會記得之前的對話
```

### 4. 使用 Interrupt 進行人工審核

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = parent_graph.compile(
    checkpointer=memory,
    interrupt_before=["rag_agent"]  # 在 RAG 執行前暫停
)

# 第一步：系統暫停等待確認
result = app.invoke(input_state, config={"configurable": {"thread_id": "1"}})

# 人工審核後繼續
result = app.invoke(None, config={"configurable": {"thread_id": "1"}})
```

### 5. 自訂 RAG 配置參數

```python
# 精細控制 RAG 行為
custom_config = RAGConfig(
    conn_string=os.getenv("PGVECTOR_URL"),
    embed_api_base=os.getenv("EMBED_API_BASE"),
    embed_api_key=os.getenv("EMBED_API_KEY"),
    top_k=15,                    # 檢索更多文件
    content_max_length=1000,     # 更長的內容
    verify_ssl=False,            # 停用 SSL 驗證
    temperature=0.2,             # 稍微增加創造力
    embed_model="custom/model"   # 自訂嵌入模型
)

rag_subgraph = create_rag_subgraph(llm, custom_config)
```

---

## 常見問題

### Q1: 如何除錯 Subgraph？

**A**: 啟用日誌模式

```python
from rag_system.common import set_quiet_mode
import logging

# 啟用詳細日誌
set_quiet_mode(False)
logging.basicConfig(level=logging.INFO)
logging.getLogger("langgraph").setLevel(logging.DEBUG)
logging.getLogger("rag_system").setLevel(logging.INFO)

# 現在執行會看到詳細過程
result = app.invoke(...)
```

### Q2: RAG Agent 可以與其他 Agent 共享對話歷史嗎？

**A**: 可以！這正是 MessagesState 的優勢。

```python
# User: "台灣有哪些懲罰法規？"
# RAG Agent 回答...

# User: "那第24條呢？"
# RAG Agent 可以從 messages 取得上下文
```

### Q3: 如何處理 RAG Agent 執行錯誤？

**A**: Subgraph 內部會捕捉錯誤並返回錯誤訊息，不會中斷 parent graph。

```python
# RAG agent 內部錯誤處理
try:
    result = agent_executor.invoke(...)
except Exception as e:
    return {"generation": f"抱歉，處理問題時發生錯誤: {str(e)}"}
```

你可以在 parent graph 加入錯誤處理邏輯：

```python
def error_handler(state):
    if "錯誤" in state['messages'][-1].content:
        # 重試或轉給 fallback agent
        return {"current_agent": "fallback_agent"}
```

### Q4: RAG Agent 效能如何優化？

**A**: 幾個優化方向

1. **減少檢索文件數量**：
   ```python
   config = RAGConfig(top_k=5)  # 預設 10
   ```

2. **縮短文件內容**：
   ```python
   config = RAGConfig(content_max_length=500)  # 預設 800
   ```

3. **快取向量搜尋結果**（進階）：
   - 在 parent graph 層實現快取機制

4. **平行執行多個 Agent**（LangGraph 支援）

### Q5: 可以動態切換 Collection 嗎？

**A**: 可以！兩種方式：

**方式 1: 在問題中指定**
```python
# RAG agent 的 router 工具會自動處理
result = app.invoke({
    "messages": [HumanMessage("使用'陸海空軍懲罰法'回答: 第24條")]
})
```

**方式 2: 建立多個專門的 Subgraph**
```python
law1_config = RAGConfig(default_collection="陸海空軍懲罰法")
law2_config = RAGConfig(default_collection="著作權法")

graph.add_node("military_law", create_rag_subgraph(llm, law1_config))
graph.add_node("copyright_law", create_rag_subgraph(llm, law2_config))
```

### Q6: 如何測試 Subgraph 是否正確整合？

**A**: 使用內建測試函數

```python
from rag_system.subgraph import test_subgraph_standalone
from rag_system.config import RAGConfig

# 快速測試
config = RAGConfig.from_env()
result = test_subgraph_standalone("陸海空軍懲罰法第24條", config)

print(result['generation'])  # 應該看到正確答案
```

### Q7: Parent Graph 和 Subgraph 可以用不同的 LLM 嗎？

**A**: 可以！

```python
# Router 用快速便宜的模型
router_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# RAG 用強大的模型
rag_llm = ChatOpenAI(model="gpt-4", temperature=0)

# 分別建立
router = create_router_node(router_llm)
rag_subgraph = create_rag_subgraph(rag_llm, rag_config)
```

---

## 最佳實踐

### 1. State Schema 一致性
✅ Parent graph 和所有 subgraph 都使用 `MessagesState` 或其子類

### 2. 錯誤處理
✅ Subgraph 內部捕捉錯誤，避免中斷整個 workflow

### 3. 日誌管理
✅ 使用統一的 `log()` 函數，方便追蹤多 agent 執行流程

### 4. 配置隔離
✅ 每個 subgraph 使用獨立的 `RAGConfig`，避免衝突

### 5. 模組化設計
✅ 將 router、formatter 等邏輯抽成獨立函數，方便重用

---

## 下一步

- 查看 [完整架構設計](#架構設計) 了解內部實現
- 執行 [examples/parent_agent.py](../examples/parent_agent.py) 體驗完整系統
- 參考 [LangGraph Multi-Agent 文件](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- 探索 [Subgraph Streaming](https://langchain-ai.github.io/langgraph/how-tos/subgraph/#stream-subgraph-outputs)

---

## Subgraph 模式 - 多代理系統整合

### 概述

從 v0.3.0 開始，RAG agent 支援作為 **subgraph** 嵌入到更大的多代理系統中。這讓你可以將法律問答功能整合為複雜 workflow 的一個專業節點。

### 架構優勢

**Standalone Mode（獨立模式）**：
```
CLI → RAG Agent → 回答
```

**Subgraph Mode（子圖模式）**：
```
Parent Graph → Router → [RAG Agent | Weather Agent | Calculator] → Formatter → 回答
```

### 核心設計

#### 1. State 相容性

RAG agent 的 state 已改為繼承 `MessagesState`：

```python
from langgraph.graph import MessagesState

class GraphState(MessagesState):
    """支援 parent graph 整合的 state schema"""
    question: str = ""        # 獨立模式相容
    generation: str = ""      # 最終答案
    collection: str = ""      # 路由結果
    retrieved_docs: list = [] # 檢索結果
    # messages 繼承自 MessagesState
```

這讓 RAG agent 可以：
- ✅ 獨立運作（使用 `question` 欄位）
- ✅ 作為 subgraph（使用 `messages` 欄位）
- ✅ 與其他 agent 共享對話歷史

#### 2. Subgraph 建立

使用 `subgraph.py` 模組建立可嵌入的 RAG agent：

```python
from rag_system.config import RAGConfig
from rag_system.subgraph import create_rag_subgraph
from langchain_openai import ChatOpenAI

# 設定
llm = ChatOpenAI(model="gpt-4", temperature=0)
config = RAGConfig.from_env()

# 建立 subgraph
rag_subgraph = create_rag_subgraph(llm, config, name="rag_legal_expert")
```

#### 3. Parent Graph 整合

將 RAG agent 作為一個節點加入 parent graph：

```python
from langgraph.graph import StateGraph, MessagesState, END

# 建立 parent graph
parent_graph = StateGraph(MessagesState)

# 加入 RAG subgraph 作為節點
parent_graph.add_node("rag_agent", rag_subgraph)
parent_graph.add_node("other_agent", other_subgraph)

# 設定路由邏輯
parent_graph.set_entry_point("router")
parent_graph.add_conditional_edges(
    "router",
    route_to_agent,
    {
        "rag_agent": "rag_agent",
        "other_agent": "other_agent"
    }
)
parent_graph.add_edge("rag_agent", END)

# 編譯
app = parent_graph.compile()
```

### 使用範例

#### 完整多代理系統範例

參見 [examples/parent_agent.py](../examples/parent_agent.py)，展示如何建構包含以下 agent 的系統：

- **Router Agent**: 智慧分配問題到專業 agent
- **RAG Agent**: 法律文件問答（subgraph）
- **Weather Agent**: 天氣查詢
- **Calculator Agent**: 數學計算
- **General Agent**: 一般對話

執行範例：
```bash
python examples/parent_agent.py
```

#### 快速整合模板

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, END
from rag_system.config import RAGConfig
from rag_system.subgraph import create_rag_subgraph

# 1. 設定
llm = ChatOpenAI(model="gpt-4", temperature=0)
rag_config = RAGConfig.from_env()

# 2. 建立 parent graph
graph = StateGraph(MessagesState)

# 3. 加入 RAG subgraph
rag_node = create_rag_subgraph(llm, rag_config)
graph.add_node("rag_specialist", rag_node)

# 4. 設定 workflow
graph.set_entry_point("rag_specialist")
graph.add_edge("rag_specialist", END)

# 5. 執行
app = graph.compile()
result = app.invoke({
    "messages": [("user", "陸海空軍懲罰法第24條")]
})
```

### State 轉換邏輯

RAG agent 的 `node.py` 會自動處理兩種模式：

**Standalone Mode 輸入**：
```python
state = {
    "question": "陸海空軍懲罰法第24條",
    "generation": ""
}
```

**Subgraph Mode 輸入**：
```python
state = {
    "messages": [HumanMessage(content="陸海空軍懲罰法第24條")],
    "question": "",
    "generation": ""
}
```

Agent node 會檢測輸入模式並適當轉換。

### 向下相容性

所有既有功能**完全保留**：

```bash
# 獨立模式仍然可用
python -m rag_system.query_rag_pg -q "陸海空軍懲罰法第24條"
./query.sh "螺旋槳推力係數如何計算？"
```

Subgraph 功能為**選用**，不影響現有使用方式。

### Subgraph API 參考

#### `create_rag_subgraph(llm, config, name)`

建立 RAG subgraph。

**參數**：
- `llm` (ChatOpenAI): 語言模型實例
- `config` (RAGConfig): RAG 系統設定
- `name` (str): Subgraph 名稱（預設: "rag_agent"）

**返回**：
- `StateGraph`: 編譯好的 subgraph，可作為 parent graph 的節點

#### `create_rag_subgraph_from_args(...)`

從個別參數建立 subgraph（便利函數）。

**參數**：
- `llm`: 語言模型
- `conn_string`: PostgreSQL 連接字串
- `embed_api_base`: API base URL
- `embed_api_key`: API key
- `embed_model`: 嵌入模型名稱
- `verify_ssl`: SSL 驗證開關
- `top_k`: 檢索文件數量
- `content_max_length`: 文件內容最大長度
- `name`: Subgraph 名稱

#### `test_subgraph_standalone(question, config)`

獨立測試 subgraph 功能。

### 最佳實踐

1. **State Schema 一致性**：Parent graph 和 subgraph 都使用 `MessagesState` 確保相容
2. **錯誤處理**：Subgraph 內部會捕捉錯誤並返回錯誤訊息，不會中斷 parent graph
3. **日誌管理**：使用 `common.log()` 統一日誌，方便除錯多 agent 系統
4. **配置隔離**：每個 subgraph 使用獨立的 `RAGConfig`，避免配置衝突

### 進階應用

#### 串聯多個 Subgraph

```python
# Supervisor pattern
graph.add_node("rag_taiwan_law", create_rag_subgraph(llm, tw_config))
graph.add_node("rag_us_law", create_rag_subgraph(llm, us_config))
graph.add_conditional_edges("router", route_by_jurisdiction)
```

#### 使用 Interrupt 進行人工審核

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = parent_graph.compile(checkpointer=memory)

# 在 RAG 回答後暫停給人工審核
result = app.invoke(input_state, config={"configurable": {"thread_id": "1"}})
```

## 版本歷史

### v0.3.0 (2025-10-02)
- ✨ **重大更新**: 支援 Subgraph 模式，可嵌入 parent graph
- ✨ State schema 改為繼承 `MessagesState`
- ✨ 新增 `subgraph.py` - subgraph 包裝層
- ✨ 新增 `examples/parent_agent.py` - 多代理系統範例
- ✨ Node 支援雙模式（standalone / subgraph）
- 📝 完整的 subgraph 整合文件

### v0.2.0 (2025-09-30)
- ✨ 新增 `article_lookup.py` 條文精確查詢工具
- ✨ 實現 hybrid search（向量 + metadata filtering）
- 🐛 修正 SSL 驗證導致的連線問題
- 📝 更新系統架構文件

### v0.1.0 (Initial)
- ✨ ReAct Agent 架構實現
- ✨ Collection 智慧路由
- ✨ 向量檢索功能
- 📝 建立初始文件

## 參考資料

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [LangGraph Subgraph How-to](https://langchain-ai.github.io/langgraph/how-tos/subgraph/)
- [LangGraph Multi-Agent Architectures](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [create_react_agent API](https://python.langchain.com/api_reference/langgraph/prebuilt/langgraph.prebuilt.chat_agent_executor.create_react_agent.html)
- [PGVector Documentation](https://github.com/pgvector/pgvector)
- ai-innovation-AI-Agent 專案架構