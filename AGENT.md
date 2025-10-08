# RAG 智能體參考指南

## 目標
- 提供單一智能體，既能回覆中文法律查詢，也能支援 DATCOM `.dat` 檔案生成任務。
- 結合檢索增強式生成（RAG）與 LangGraph 路由，讓系統可在固定工程流程與彈性 ReAct 迴圈之間切換。
- 採用統一元件，可獨立以 CLI (`rag_system/query_rag_pg.py`) 執行，或以子圖方式嵌入更大規模的多智能體系統（`rag_system/subgraph.py`）。

## 工作流程概覽
```
[使用者問題]
      │
      ▼
路由節點 ──► datcom_generation? ──► DATCOM 固定序列節點 ──► END
      │
      └────► general_query ─────────► ReAct 智能體節點 ───────► END
```
- `rag_system/agent.py` 建立 LangGraph `StateGraph`，所有進入點皆沿用此流程。
- 判斷依據 `GraphState.intent`（參見 `rag_system/state.py`）。
- 兩個分支最終皆將答案寫入狀態的 `generation` 欄位並回傳。

## 狀態管理
- `GraphState` 繼承 LangGraph 的 `MessagesState`，可同時支援父層流程與舊版字典格式的狀態管理。
- 主要欄位：`messages`、`question`、`generation`、`collection`、`retrieved_docs`、`intent`。
- `LegacyGraphState` 僅用於維持早期程式碼相容性（`TypedDict` 版本）。

## 路由邏輯（`rag_system/router_node.py`）
- `create_intent_router_node` 使用 `ChatOpenAI` 加上輕量提示詞（`ROUTER_SYSTEM_PROMPT`）建立。
- 節點會檢查使用者 `question` 是否出現生成關鍵字（如「生成 .dat」）或明確的空氣動力參數，判定走 `datcom_generation` 或 `general_query`。
- 若模型回傳結果含糊，則預設回到 `general_query`，並建立 `messages`，確保後續節點擁有一致的對話歷程。

## DATCOM 固定序列（`rag_system/datcom_node.py`）
1. **參數擷取**：LLM 將請求解析為 `DatcomParams`，僅保留明確指定的數值。
2. **檢核**：必須包含基本機翼幾何與飛行條件，否則回傳中文釐清訊息。
3. **工具鏈**：按固定順序呼叫 `convert_wing_to_datcom`、`generate_fltcon_matrix`、（選配）`calculate_synthesis_positions`、`define_body_geometry`、尾翼轉換工具。缺漏的尾翼參數會依機翼比例估算。
4. **格式化**：`_build_datcom_format` 整合工具回傳結果，輸出符合 DATCOM `.dat` 格式的結果。
- 透過 `common.log` 產生階段性日誌，顯示「--- RUNNING DATCOM FIXED SEQUENCE ---」等提示。

## 一般 ReAct 智能體（`rag_system/node.py`）
- 以 `langgraph.prebuilt.create_react_agent` 建構。
- 可使用完整工具集（檢索、後設資料搜尋、計算器、DATCOM 計算工具）。
- `messages` 僅保留最近四則對話，避免模型上下文過長。
- 輸出 Markdown 風格答案：
  - 若 LLM 回覆內容充足即直接採用。
  - 若回覆空白或過短，則改由 `_build_standard_format` 統整工具回傳內容。

## 工具總表（`rag_system/tool/`）
| 模組 | 工具／工廠函式 | 功能 | 備註 |
| --- | --- | --- | --- |
| `router.py` | `create_router_tool` | 以 LLM 選出最佳 PGVector collection（設計領域）。 | 依賴 `build.db_utils.get_collection_stats`。 |
| `retrieve.py` | `create_retrieve_tool` | 在 PGVector collection 進行語義檢索。 | 回傳附來源資訊的文件片段。 |
| `metadata_search.py` | `create_metadata_search_tool` | 依後設資料（條文、頁碼、來源）做精確過濾。 | 透過 SQLAlchemy 執行 SQL。 |
| `article_lookup.py` | `create_article_lookup_tool` | 快速查詢特定法律條文。 | 以正則擷取條號後查詢。 |
| `calculator.py` | `create_calculator_tool` | 安全執行 Python 數學運算。 | 僅提供數學相關命名空間。 |
| `datcom_calculator.py` | `create_datcom_calculator_tools` | 將空氣動力參數轉為 DATCOM namelist。 | 含驗證工具、`validate_datcom_parameters`。 |

## 資料與索引流程（`rag_system/build/`）
1. `preprocess.py` → 將 `rag_system/documents/` 的原始 PDF、RTF… 轉成清理後的 Markdown（存於 `rag_system/processed_md/`）。
2. `chunking.py` → 依法律文本特徵（如「第X條」、「第X章」、條列）或一般規則拆分。
3. `structure_detector.py` → 綜合正則與選用 LLM 來判斷拆分策略。
4. `indexer.py` → 匯出分塊成果、呼叫 `LocalApiEmbeddings` 產生向量，寫入 PGVector collection。
5. `build_all.sh` → 自動化上述流程，可選擇增量或強制重建模式。

## 設定與環境
- `.env.example` 提供必要環境變數：`PGVECTOR_URL`、`EMBED_API_BASE`、`LLM_API_BASE`、`EMBED_API_KEY` 及模型、SSL 相關設定。
- `RAGConfig`（`rag_system/config.py`）負責驗證與載入設定，供 CLI 與子圖共用。
- 常用執行參數：
  - 檢索量：`top_k`、`content_max_length`。
  - 模型選擇：`embed_model`、`chat_model`、`temperature`。
  - SSL 驗證：`verify_ssl`。

## 執行智能體
- **CLI 入口**：`python rag_system/query_rag_pg.py -q "<question>"`，可搭配 `--collection`、`--top-k`、`--debug`。
  - `--retrieve-only` 只輸出檢索結果 JSON，不呼叫 LLM。
  - 若省略 `-q`，則進入互動模式。
- **Shell 腳本**：`query.sh` 以專案預設值呼叫 CLI。
- **程式呼叫**：可直接匯入 `build_workflow` 或 `create_rag_subgraph` 在程式中執行。

## 子圖整合（`rag_system/subgraph.py`）
- `create_rag_subgraph(llm, RAGConfig, name)` 會編譯相同工作流程並共享工具。
- 設計用於整合至其他 LangGraph 主管節點：加入條件邊、注入 `GraphState` 訊息、在完成後讀取 `generation`。
- `create_rag_subgraph_from_args` 提供以參數快速建構設定的捷徑。

## 日誌與診斷
- `common.log` 預設輸出 `[LOG] ...`，可透過 `set_quiet_mode(True)` 靜音。
- CLI `--debug` 會啟用 LangChain／LangGraph 詳細日誌並關閉靜音模式。
- DATCOM 序列及路由節點皆會輸出結構化日誌，便於追蹤決策流程。
- `common.LocalApiEmbeddings` 對 HTTP 請求提供重試與詳細錯誤訊息，協助排查批次嵌入失敗。

## 資料夾導覽
- `rag_system/`：智能體執行流程、LangGraph 工作流、工具與共用模組。
- `rag_system/build/`：離線建索流程（PGVector 資料建置）。
- `docs/`：補充文件（`DEVELOPER_GUIDE.md`、架構圖等）。
- `examples/`：示例輸入或提示（若有提供）。
- `docker/`、`docker-compose.yaml`、`Dockerfile`：PostgreSQL + pgvector 執行環境。
- `GEMINI.md`、`ROADMAP.md`：其他專案筆記。

## 相關文件
- `README.md`：建置與查詢的快速入門。
- `docs/DEVELOPER_GUIDE.md`：架構與開發流程的詳細說明。
- `ROADMAP.md`：未來計畫與研發方向。
