# build_all.sh 使用指南

## 功能說明

自動化 RAG 建置流程腳本，包含：
1. 文件預處理（轉換為 Markdown）
2. 建立資料庫 collection（向量嵌入與索引）

## 智慧增量建置

預設行為：**跳過已存在的 collection**，僅建立新的或缺失的 collection。

## 使用方式

### 基本用法（增量建置）

```bash
./build_all.sh
```

**行為**：
- ✅ 執行文件預處理
- ✅ 檢查每個 collection 是否存在
- ⏭️ 跳過已存在的 collection
- 🔨 僅建立新的 collection

**適用場景**：
- 新增文件到專案
- 首次建置
- 正常開發流程

### 強制重建所有 collection

```bash
./build_all.sh --force
# 或
./build_all.sh -f
```

**行為**：
- ✅ 執行文件預處理
- 🔄 強制重建所有 collection（即使已存在）
- ⚠️ 會刪除並重建現有資料

**適用場景**：
- 修改了切分策略（split strategy）
- 更新了嵌入模型
- 資料損壞需要重建
- 修改了文件內容需要完整更新

### 僅重建（跳過預處理）

```bash
./build_all.sh --rebuild-only
# 或
./build_all.sh -r
```

**行為**：
- ⏭️ 跳過文件預處理步驟
- 🔨 直接從現有 Markdown 建立 collection
- ⏭️ 跳過已存在的 collection

**適用場景**：
- Markdown 檔案已存在且正確
- 只需要更新資料庫
- 預處理步驟耗時且不需要重複執行

### 組合使用

```bash
# 強制重建 + 跳過預處理
./build_all.sh --force --rebuild-only
```

## 輸出範例

### 增量建置輸出

```
--- Starting RAG Build Process ---
Mode: INCREMENTAL (skip existing collections)

[STEP 1/2] Preprocessing source documents into Markdown...
...

[STEP 2/2] Building database collections from Markdown files...
Found 3 markdown file(s) to process.

-----------------------------------------------------
Processing: '陸海空軍懲罰法' from rag_system/processed_md/陸海空軍懲罰法.md
⏭️  SKIPPED: Collection '陸海空軍懲罰法' already exists
    (Use --force to rebuild)

-----------------------------------------------------
Processing: '軍人權益事件處理法' from rag_system/processed_md/軍人權益事件處理法.md
⏭️  SKIPPED: Collection '軍人權益事件處理法' already exists
    (Use --force to rebuild)

-----------------------------------------------------
Processing: '新增文件' from rag_system/processed_md/新增文件.md
🔨 BUILDING: Collection '新增文件'
-----------------------------------------------------
...

-----------------------------------------------------
--- RAG Build Process Complete ---

Summary:
  • Total files processed: 3
  • Collections built: 1
  • Collections skipped: 2

Tip: Use './build_all.sh --force' to rebuild all collections
```

### 強制重建輸出

```
--- Starting RAG Build Process ---
Mode: FORCE REBUILD (all collections will be recreated)

[STEP 1/2] Preprocessing source documents into Markdown...
...

[STEP 2/2] Building database collections from Markdown files...
Found 3 markdown file(s) to process.

-----------------------------------------------------
Processing: '陸海空軍懲罰法' from rag_system/processed_md/陸海空軍懲罰法.md
🔄 REBUILDING: Collection '陸海空軍懲罰法'
-----------------------------------------------------
...

Summary:
  • Total files processed: 3
  • Collections built: 3
  • Collections skipped: 0
```

## Collection 檢測機制

腳本自動檢測 PostgreSQL 資料庫中的 collection：

1. **尋找 Docker 容器**：
   - 優先使用 `docker compose ps`
   - 降級使用 image 名稱搜尋

2. **查詢資料庫**：
   ```sql
   SELECT COUNT(*) FROM langchain_pg_collection WHERE name='collection_name';
   ```

3. **決策邏輯**：
   - COUNT > 0 → Collection 存在 → 跳過（除非 --force）
   - COUNT = 0 → Collection 不存在 → 建立
   - 容器未運行 → 假設不存在 → 建立

## 故障排除

### 問題：腳本無法檢測已存在的 collection

**可能原因**：
- PostgreSQL 容器未運行
- 容器名稱或 image 已變更

**解決方案**：
```bash
# 確認容器運行
docker ps

# 手動檢查 collection
docker exec <container_id> psql -U postgres -c "SELECT name FROM langchain_pg_collection;"
```

### 問題：想要重建特定 collection

**解決方案**：
```bash
# 方法 1: 手動刪除 collection 後重建
docker exec <container_id> psql -U postgres -c "DELETE FROM langchain_pg_collection WHERE name='collection_name';"
./build_all.sh

# 方法 2: 強制重建全部（簡單但較慢）
./build_all.sh --force
```

### 問題：預處理後 Markdown 正確但 collection 建立失敗

**解決方案**：
```bash
# 只重建 collection，不重新預處理
./build_all.sh --rebuild-only
```

## 技術細節

### 檔案處理流程

1. **文件預處理**：
   - 輸入：`rag_system/documents/`
   - 輸出：`rag_system/processed_md/`
   - 處理：PDF → Markdown，保留結構

2. **Collection 建立**：
   - 輸入：`rag_system/processed_md/*.md`
   - Collection 名稱：檔案名稱（去除 .md）
   - 處理：切分 → 嵌入 → 入庫

### 參數傳遞

```bash
python3 -m rag_system.build.indexer \
  --input_file "$md_file" \
  --collection "$collection_name" \
  --reset_collection \    # 清空現有資料
  --embed \                # 執行嵌入
  --no-verify-ssl          # 停用 SSL 驗證（開發用）
```

## 最佳實踐

### 開發流程

1. **首次建置**：
   ```bash
   ./build_all.sh
   ```

2. **新增文件**：
   - 將文件放入 `rag_system/documents/`
   - 執行 `./build_all.sh`（自動跳過已存在的）

3. **修改文件內容**：
   - 更新 `rag_system/documents/` 中的檔案
   - 執行 `./build_all.sh --force`（重建全部）

4. **修改切分策略**：
   - 修改 `rag_system/build/indexer.py`
   - 執行 `./build_all.sh --force --rebuild-only`

### 效能優化

- ⚡ **跳過預處理**：使用 `--rebuild-only` 節省 30-50% 時間
- ⚡ **增量建置**：預設行為避免重複建立
- ⚡ **批次處理**：腳本自動處理多個檔案

### 安全考量

- ⚠️ `--force` 會刪除現有資料，使用前請確認
- ⚠️ 生產環境應移除 `--no-verify-ssl` 參數
- ⚠️ Collection 名稱直接來自檔案名，避免特殊字元

## 相關文件

- [REACT_AGENT_README.md](rag_system/REACT_AGENT_README.md) - Agent 架構說明
- [README.md](README.md) - 專案總覽
- `.env` - 環境變數配置