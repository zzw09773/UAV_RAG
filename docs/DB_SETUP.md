# Database Setup Guide

本指南說明如何設定 PostgreSQL + PGVector 資料庫以支援 RAG 系統。

## 方案 A：使用 Docker Compose（推薦）

### 1. 啟動資料庫

```bash
cd rag_system
docker compose up -d pgvector
```

### 2. 驗證資料庫運行

```bash
# 檢查容器狀態
docker compose ps

# 應該看到
# NAME      COMMAND                 STATUS        PORTS
# rag_db    "docker-entrypoint.s…"  Up (healthy)  0.0.0.0:5433->5432/tcp
```

### 3. 連接測試

```bash
# 使用 psql 連接
docker exec -it rag_db psql -U postgres -d postgres

# 在 psql 中測試 pgvector
postgres=# SELECT * FROM pg_extension WHERE extname = 'vector';
```

應該看到 `vector` 擴展已安裝。

### 4. 停止資料庫

```bash
# 停止但保留數據
docker compose stop

# 停止並移除容器（數據保留在 volume 中）
docker compose down

# 完全清除（包括數據）
docker compose down -v
```

---

## 方案 B：手動安裝 PostgreSQL + PGVector

### Ubuntu/Debian

```bash
# 1. 安裝 PostgreSQL 17
sudo apt update
sudo apt install -y postgresql-17 postgresql-client-17

# 2. 安裝 PGVector
sudo apt install -y postgresql-17-pgvector

# 3. 啟動服務
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 4. 建立資料庫使用者
sudo -u postgres psql -c "CREATE USER rag_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE rag_db OWNER rag_user;"

# 5. 啟用 pgvector 擴展
sudo -u postgres psql -d rag_db -c "CREATE EXTENSION vector;"
```

### macOS (Homebrew)

```bash
# 1. 安裝 PostgreSQL
brew install postgresql@17

# 2. 安裝 PGVector
brew install pgvector

# 3. 啟動服務
brew services start postgresql@17

# 4. 建立資料庫
createdb rag_db

# 5. 啟用擴展
psql rag_db -c "CREATE EXTENSION vector;"
```

### 更新 .env 設定

```bash
# 修改 .env 檔案中的連接字串
PGVECTOR_URL="postgresql+psycopg2://rag_user:your_password@localhost:5432/rag_db"
```

---

## 資料庫架構

### PGVector Extension

系統使用 `pgvector` 儲存向量嵌入：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Collection Tables

系統會自動為每個 collection 建立以下資料表：

```sql
-- 自動建立（透過 LangChain PGVector）
CREATE TABLE langchain_pg_collection (
    uuid UUID PRIMARY KEY,
    name VARCHAR,
    cmetadata JSONB
);

CREATE TABLE langchain_pg_embedding (
    uuid UUID PRIMARY KEY,
    collection_id UUID REFERENCES langchain_pg_collection(uuid),
    embedding VECTOR(4096),  -- 根據模型維度調整
    document TEXT,
    cmetadata JSONB
);

-- 向量搜尋索引
CREATE INDEX ON langchain_pg_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 常見問題

### Q1: 連接被拒絕 (Connection refused)

**問題**：
```
psycopg2.OperationalError: could not connect to server
```

**解決**：
1. 確認資料庫已啟動：`docker compose ps` 或 `systemctl status postgresql`
2. 檢查連接埠是否正確（Docker 預設 5433，本地預設 5432）
3. 檢查防火牆設定

### Q2: pgvector 擴展不存在

**問題**：
```
ERROR: extension "vector" does not exist
```

**解決**：
```bash
# Docker Compose 方式
docker compose down -v
docker compose up -d  # 自動執行 init SQL

# 手動方式
psql -d your_database -c "CREATE EXTENSION vector;"
```

### Q3: 權限錯誤

**問題**：
```
ERROR: permission denied for database
```

**解決**：
```sql
-- 授予使用者權限
GRANT ALL PRIVILEGES ON DATABASE rag_db TO rag_user;
GRANT ALL ON SCHEMA public TO rag_user;
```

### Q4: Docker volume 數據損壞

**解決**：
```bash
# 完全重置資料庫
docker compose down -v
docker volume rm rag_system_pgdata  # 確認 volume 名稱
docker compose up -d
```

---

## 效能調優

### 向量索引優化

```sql
-- IVFFlat 索引（快速但略犧牲精確度）
CREATE INDEX embedding_idx ON langchain_pg_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- HNSW 索引（更精確但較慢）
CREATE INDEX embedding_hnsw_idx ON langchain_pg_embedding
USING hnsw (embedding vector_cosine_ops);
```

### PostgreSQL 設定調整

編輯 `postgresql.conf` 或在 Docker Compose 中設定：

```yaml
# docker-compose.yaml
environment:
  POSTGRES_INITDB_ARGS: "-c shared_buffers=256MB -c max_connections=100"
```

---

## 資料備份與還原

### 備份

```bash
# 備份整個資料庫
docker exec rag_db pg_dump -U postgres postgres > backup.sql

# 只備份特定 collection
docker exec rag_db pg_dump -U postgres -t langchain_pg_* postgres > collections_backup.sql
```

### 還原

```bash
# 還原資料庫
cat backup.sql | docker exec -i rag_db psql -U postgres postgres
```

---

## 監控與維護

### 檢查資料庫大小

```sql
SELECT
    pg_size_pretty(pg_database_size('postgres')) as db_size,
    (SELECT COUNT(*) FROM langchain_pg_embedding) as total_vectors;
```

### 清理無用數據

```sql
-- 刪除特定 collection
DELETE FROM langchain_pg_collection WHERE name = 'old_collection';

-- Vacuum 釋放空間
VACUUM FULL;
```

### 查看連接數

```sql
SELECT count(*) FROM pg_stat_activity;
```

---

## 進階配置

### 使用外部 PostgreSQL 服務

如果使用 AWS RDS、Google Cloud SQL 等託管服務：

1. 確保 pgvector 擴展已啟用
2. 更新 `.env` 設定：

```bash
PGVECTOR_URL="postgresql+psycopg2://user:password@your-rds-endpoint:5432/dbname"
```

3. 配置安全組/防火牆規則允許連接

### SSL 連接

```bash
PGVECTOR_URL="postgresql+psycopg2://user:password@host:5432/db?sslmode=require"
```

---

## 參考資源

- [PGVector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Official Docs](https://www.postgresql.org/docs/)
- [LangChain PGVector Integration](https://python.langchain.com/docs/integrations/vectorstores/pgvector)