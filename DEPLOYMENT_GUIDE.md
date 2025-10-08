# UAV RAG 系統內網部署指南

本指南說明如何在內網環境中從零開始部署 UAV RAG 系統。

## 📋 目錄

- [系統需求](#系統需求)
- [前置準備](#前置準備)
- [步驟 1: 準備 PostgreSQL 資料庫](#步驟-1-準備-postgresql-資料庫)
- [步驟 2: 複製專案到內網](#步驟-2-複製專案到內網)
- [步驟 3: 安裝 Python 依賴](#步驟-3-安裝-python-依賴)
- [步驟 4: 配置環境變數](#步驟-4-配置環境變數)
- [步驟 5: 初始化向量資料庫](#步驟-5-初始化向量資料庫)
- [步驟 6: 建立文件索引](#步驟-6-建立文件索引)
- [步驟 7: 啟動查詢服務](#步驟-7-啟動查詢服務)
- [故障排除](#故障排除)

---

## 系統需求

### 硬體需求
- **CPU**: 4 核心以上
- **記憶體**: 8GB 以上 (建議 16GB)
- **硬碟**: 20GB 可用空間

### 軟體需求
- **作業系統**: Linux (Ubuntu 20.04+ / CentOS 7+ / RHEL 8+)
- **Python**: 3.10 或 3.11
- **PostgreSQL**: 12 或更高版本 (需支援 pgvector extension)
- **Git**: 用於複製專案 (可選,也可用 USB 傳輸)

---

## 前置準備

### 1. 確認 Python 版本
```bash
python3 --version
# 應顯示: Python 3.10.x 或 3.11.x
```

如果版本不符,需要先升級 Python。

### 2. 安裝必要的系統套件
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git libpq-dev build-essential

# CentOS/RHEL
sudo yum install -y python3-pip python3-devel git postgresql-devel gcc
```

---

## 步驟 1: 準備 PostgreSQL 資料庫

### 選項 A: 使用現有的 PostgreSQL 伺服器

1. **安裝 pgvector extension**
   ```bash
   # 登入 PostgreSQL
   sudo -u postgres psql
   
   # 建立資料庫
   CREATE DATABASE rag_db;
   
   # 連接到資料庫
   \c rag_db
   
   # 安裝 pgvector extension
   CREATE EXTENSION IF NOT EXISTS vector;
   
   # 確認安裝成功
   \dx
   # 應該看到 "vector" 在列表中
   
   # 離開
   \q
   ```

2. **建立專用使用者 (可選,建議)**
   ```bash
   sudo -u postgres psql
   
   CREATE USER rag_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE rag_db TO rag_user;
   \q
   ```

### 選項 B: 全新安裝 PostgreSQL

1. **安裝 PostgreSQL 12+**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y postgresql postgresql-contrib
   
   # CentOS/RHEL
   sudo yum install -y postgresql-server postgresql-contrib
   sudo postgresql-setup initdb
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **安裝 pgvector extension**
   
   參考官方文件: https://github.com/pgvector/pgvector
   
   ```bash
   # 下載並編譯 pgvector
   cd /tmp
   git clone https://github.com/pgvector/pgvector.git
   cd pgvector
   make
   sudo make install
   ```
   
   如果內網無法 git clone,可以在外網下載 pgvector 原始碼後用 USB 傳入。

3. **建立資料庫並啟用 extension** (同選項 A)

---

## 步驟 2: 複製專案到內網

### 方法 A: 使用 Git (如果內網可連外部 Git)
```bash
cd /path/to/your/workspace
git clone https://github.com/zzw09773/UAV_RAG.git
cd UAV_RAG
git checkout Test  # 切換到 Test 分支
```

### 方法 B: 使用 USB 傳輸 (推薦內網使用)

1. **在外網機器上打包專案**
   ```bash
   # 外網機器
   cd /path/to/UAV_RAG
   git checkout Test
   tar -czf UAV_RAG.tar.gz .
   # 將 UAV_RAG.tar.gz 複製到 USB
   ```

2. **在內網機器上解壓**
   ```bash
   # 內網機器
   mkdir -p /opt/uav_rag
   cd /opt/uav_rag
   tar -xzf /path/to/USB/UAV_RAG.tar.gz
   ```

---

## 步驟 3: 安裝 Python 依賴

### 3.1 建立虛擬環境
```bash
cd /opt/uav_rag
python3 -m venv venv
source venv/bin/activate
```

### 3.2 升級 pip
```bash
pip install --upgrade pip
```

### 3.3 安裝依賴套件

#### 選項 A: 線上安裝 (內網有 PyPI mirror)
```bash
pip install -r requirements.txt
```

#### 選項 B: 離線安裝 (推薦內網使用)

1. **在外網機器準備離線套件**
   ```bash
   # 外網機器
   cd /path/to/UAV_RAG
   mkdir -p offline_packages
   pip download -r requirements.txt -d offline_packages/
   
   # 打包
   tar -czf python_packages.tar.gz offline_packages/
   # 複製到 USB
   ```

2. **在內網機器安裝**
   ```bash
   # 內網機器
   cd /opt/uav_rag
   tar -xzf /path/to/USB/python_packages.tar.gz
   pip install --no-index --find-links=offline_packages/ -r requirements.txt
   ```

### 3.4 驗證安裝
```bash
python3 -c "
import psycopg2
from langchain.vectorstores.pgvector import PGVector
from langchain_openai import ChatOpenAI
print('✓ All core packages installed successfully')
"
```

---

## 步驟 4: 配置環境變數

### 4.1 複製環境變數範本
```bash
cp .env.example .env
# 如果沒有 .env.example,則建立新的 .env 檔案
```

### 4.2 編輯 .env 檔案
```bash
nano .env  # 或使用 vi/vim
```

### 4.3 設定必要的環境變數
```bash
# ============================================
# PostgreSQL 資料庫配置
# ============================================
PGVECTOR_URL=postgresql+psycopg2://rag_user:your_password@localhost:5432/rag_db

# 如果使用 localhost 以外的伺服器
# PGVECTOR_URL=postgresql+psycopg2://rag_user:your_password@192.168.1.100:5432/rag_db

# ============================================
# OpenAI API 配置 (或相容的 API)
# ============================================
# 如果使用內網部署的 LLM API
OPENAI_API_BASE=http://your-internal-llm-server:8000/v1
OPENAI_API_KEY=your-api-key

# LLM 模型配置
CHAT_MODEL_NAME=openai/gpt-oss-20b
LLM_API_BASE=http://your-internal-llm-server:8000/v1
LLM_API_KEY=your-api-key

# ============================================
# Embedding API 配置
# ============================================
EMBED_API_BASE=http://your-internal-embedding-server:8000/v1
EMBED_API_KEY=your-api-key
EMBED_MODEL_NAME=nvidia/nv-embed-v2

# ============================================
# 其他配置
# ============================================
# 預設集合名稱
DEFAULT_COLLECTION=laws

# 日誌等級
LOG_LEVEL=INFO
```

### 4.4 驗證環境變數
```bash
source .env
echo "Database: $PGVECTOR_URL"
echo "LLM API: $LLM_API_BASE"
```

---

## 步驟 5: 初始化向量資料庫

### 5.1 測試資料庫連接
```bash
python3 -c "
from rag_system.build.db_utils import ensure_pgvector
import os
from dotenv import load_dotenv
load_dotenv()
conn_str = os.getenv('PGVECTOR_URL')
ensure_pgvector(conn_str)
print('✓ Database connection successful')
"
```

如果出現錯誤,請檢查:
- PostgreSQL 服務是否運行: `sudo systemctl status postgresql`
- 連接字串中的使用者名稱、密碼、主機、埠號是否正確
- 防火牆設定是否允許連接

### 5.2 檢查資料庫狀態
```bash
python3 -c "
from rag_system.build.db_utils import get_collection_stats
import os
from dotenv import load_dotenv
load_dotenv()
conn_str = os.getenv('PGVECTOR_URL')
stats = get_collection_stats(conn_str)
print(f'Current collections: {len(stats)}')
for s in stats:
    print(f\"  - {s['name']}: {s['doc_count']} documents\")
"
```

---

## 步驟 6: 建立文件索引

### 6.1 準備文件

將你的文件放入 `rag_system/documents/` 目錄:

```bash
# 支援的格式: .md, .pdf, .docx, .rtf, .txt
cp /path/to/your/documents/*.md rag_system/documents/
```

### 6.2 執行建立流程

```bash
# 給腳本執行權限
chmod +x build_all.sh

# 執行建立 (第一次)
./build_all.sh

# 強制重建所有集合
./build_all.sh --force

# 只重建索引,跳過預處理
./build_all.sh --rebuild-only
```

### 6.3 建立過程說明

腳本會自動執行以下步驟:

1. **預處理文件** → 將各種格式轉換為 Markdown
2. **切分文件** → 智慧切分為語義塊 (chunks)
3. **向量化** → 調用 Embedding API 生成向量
4. **儲存資料庫** → 將向量和 metadata 存入 PostgreSQL

### 6.4 驗證建立結果

```bash
python3 -c "
from rag_system.build.db_utils import get_collection_stats
import os
from dotenv import load_dotenv
load_dotenv()
conn_str = os.getenv('PGVECTOR_URL')
stats = get_collection_stats(conn_str)
print('✓ Collections built:')
for s in stats:
    print(f\"  - {s['name']}: {s['doc_count']} documents\")
"
```

---

## 步驟 7: 啟動查詢服務

### 7.1 互動式查詢 (命令列)

```bash
# 給腳本執行權限
chmod +x query.sh

# 啟動互動模式
./query.sh

# 直接查詢
./query.sh "無人機的升力係數如何計算?"

# 指定集合查詢
./query.sh -q "升力公式" --collection "無人機公式文件與RAG測試"
```

### 7.2 只檢索模式 (不使用 LLM)

```bash
./query.sh --retrieve-only --collection "無人機公式文件與RAG測試" -q "升力"
```

### 7.3 建立系統服務 (開機自動啟動,可選)

創建 systemd service 檔案:

```bash
sudo nano /etc/systemd/system/uav-rag.service
```

內容:
```ini
[Unit]
Description=UAV RAG Query Service
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/uav_rag
Environment="PATH=/opt/uav_rag/venv/bin:/usr/bin"
ExecStart=/opt/uav_rag/venv/bin/python3 -m rag_system.query_rag_pg --no-verify-ssl
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟用服務:
```bash
sudo systemctl daemon-reload
sudo systemctl enable uav-rag
sudo systemctl start uav-rag
sudo systemctl status uav-rag
```

---

## 故障排除

### 問題 1: 中文亂碼

**症狀**: 輸出顯示亂碼或 `UnicodeDecodeError`

**解決方法**:
```bash
# 方法 1: 執行 UTF-8 環境設定腳本
source ./set_utf8_env.sh

# 方法 2: 手動設定環境變數
export LANG=zh_TW.UTF-8
export LC_ALL=zh_TW.UTF-8
export PYTHONIOENCODING=utf-8
export PGCLIENTENCODING=UTF8

# 方法 3: 永久設定 (添加到 ~/.bashrc)
echo 'export LANG=zh_TW.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=zh_TW.UTF-8' >> ~/.bashrc
echo 'export PYTHONIOENCODING=utf-8' >> ~/.bashrc
source ~/.bashrc
```

### 問題 2: 資料庫連接失敗

**症狀**: `psycopg2.OperationalError: could not connect to server`

**檢查清單**:
1. PostgreSQL 服務是否運行
   ```bash
   sudo systemctl status postgresql
   ```

2. 檢查 PostgreSQL 監聽位址
   ```bash
   sudo nano /etc/postgresql/*/main/postgresql.conf
   # 確認 listen_addresses = '*' 或包含你的 IP
   ```

3. 檢查 pg_hba.conf 權限設定
   ```bash
   sudo nano /etc/postgresql/*/main/pg_hba.conf
   # 添加: host    all    all    192.168.1.0/24    md5
   ```

4. 重啟 PostgreSQL
   ```bash
   sudo systemctl restart postgresql
   ```

### 問題 3: pgvector extension 安裝失敗

**症狀**: `ERROR: could not open extension control file`

**解決方法**:
```bash
# 重新編譯安裝 pgvector
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make clean
make
sudo make install

# 重啟 PostgreSQL
sudo systemctl restart postgresql

# 重新建立 extension
sudo -u postgres psql -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 問題 4: Embedding API 連接失敗

**症狀**: `Error code: 400` 或 `Connection refused`

**檢查清單**:
1. 確認 Embedding API 伺服器正在運行
   ```bash
   curl http://your-embedding-server:8000/v1/models
   ```

2. 檢查 `.env` 中的 API 端點和 API key
   ```bash
   cat .env | grep EMBED
   ```

3. 測試連接
   ```bash
   python3 -c "
   from rag_system.common import LocalApiEmbeddings
   import os
   from dotenv import load_dotenv
   load_dotenv()
   embedder = LocalApiEmbeddings(
       api_base=os.getenv('EMBED_API_BASE'),
       api_key=os.getenv('EMBED_API_KEY'),
       model_name=os.getenv('EMBED_MODEL_NAME'),
       verify_ssl=False
   )
   result = embedder.embed_query('test')
   print(f'✓ Embedding successful, vector dimension: {len(result)}')
   "
   ```

### 問題 5: 套件版本衝突

**症狀**: `ImportError` 或 `ModuleNotFoundError`

**解決方法**:
```bash
# 重新安裝所有依賴
pip install --force-reinstall -r requirements.txt

# 檢查套件版本
pip list | grep -E "langchain|psycopg|pgvector"

# 應該看到:
# langchain-community    0.3.x
# langchain-core         0.3.x
# psycopg2-binary        2.9.10
# pgvector               0.2.x 或 0.3.x
```

### 問題 6: 記憶體不足

**症狀**: 建立索引時程式崩潰或變慢

**解決方法**:
1. 減少批次大小 (修改 `rag_system/common.py`)
   ```python
   # 在 LocalApiEmbeddings 中
   batch_size = 4  # 原本可能是 8
   ```

2. 單獨處理大文件
   ```bash
   # 一次只處理一個文件
   python3 -m rag_system.build.indexer \
     --input_file rag_system/processed_md/your_file.md \
     --collection "collection_name" \
     --embed \
     --reset_collection
   ```

---

## 效能優化建議

### 1. PostgreSQL 調校

編輯 `postgresql.conf`:
```ini
# 記憶體設定 (根據你的硬體調整)
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
work_mem = 64MB

# 連接設定
max_connections = 100

# 查詢優化
random_page_cost = 1.1  # SSD 使用
effective_io_concurrency = 200
```

### 2. 建立索引加速查詢

```sql
-- 連接到資料庫
\c rag_db

-- 為常用查詢欄位建立索引
CREATE INDEX IF NOT EXISTS idx_collection_id 
ON langchain_pg_embedding(collection_id);

CREATE INDEX IF NOT EXISTS idx_cmetadata_gin 
ON langchain_pg_embedding USING gin(cmetadata);
```

### 3. 批次處理大量文件

```bash
# 分批建立,避免一次性載入太多
for file in rag_system/processed_md/*.md; do
  echo "Processing: $file"
  python3 -m rag_system.build.indexer \
    --input_file "$file" \
    --embed \
    --no-verify-ssl
  sleep 2  # 避免 API rate limit
done
```

---

## 安全性建議

1. **資料庫安全**
   - 使用強密碼
   - 限制資料庫使用者權限
   - 定期備份資料庫
   ```bash
   pg_dump -U rag_user rag_db > backup_$(date +%Y%m%d).sql
   ```

2. **API 安全**
   - 使用 HTTPS (如果可能)
   - 定期更換 API key
   - 限制 API 訪問來源 IP

3. **檔案權限**
   ```bash
   chmod 600 .env  # 只有擁有者可讀寫
   chmod 700 build_all.sh query.sh  # 只有擁有者可執行
   ```

---

## 維護作業

### 定期備份

```bash
# 建立備份腳本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/uav_rag/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 備份資料庫
pg_dump -U rag_user rag_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 備份文件
tar -czf $BACKUP_DIR/documents_$DATE.tar.gz rag_system/documents/

# 刪除 30 天前的備份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "✓ Backup completed: $DATE"
EOF

chmod +x backup.sh

# 設定 cron 定時執行 (每天凌晨 2 點)
crontab -e
# 添加: 0 2 * * * /opt/uav_rag/backup.sh >> /opt/uav_rag/backup.log 2>&1
```

### 監控日誌

```bash
# 查看最近的錯誤
grep -i error /var/log/postgresql/*.log | tail -20

# 監控資料庫大小
psql -U rag_user -d rag_db -c "
SELECT 
  pg_size_pretty(pg_database_size('rag_db')) as db_size,
  (SELECT count(*) FROM langchain_pg_collection) as collections,
  (SELECT count(*) FROM langchain_pg_embedding) as total_docs;
"
```

---

## 聯絡支援

如遇到無法解決的問題,請提供以下資訊:

1. 作業系統版本: `cat /etc/os-release`
2. Python 版本: `python3 --version`
3. PostgreSQL 版本: `psql --version`
4. 錯誤訊息完整內容
5. `.env` 配置 (隱藏敏感資訊)

---

## 附錄

### A. 離線安裝 PostgreSQL pgvector

如果內網無法編譯,可在外網準備編譯好的 `.so` 檔案:

```bash
# 外網機器 (相同 OS 版本)
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
# 複製編譯產物
cp vector.so vector.control vector--*.sql /tmp/pgvector_install/

# 打包
tar -czf pgvector_prebuilt.tar.gz /tmp/pgvector_install/
```

內網安裝:
```bash
# 解壓到 PostgreSQL extension 目錄
sudo tar -xzf pgvector_prebuilt.tar.gz -C /usr/share/postgresql/*/extension/
sudo systemctl restart postgresql
```

### B. 環境變數完整範例

```bash
# .env 檔案完整範例
PGVECTOR_URL=postgresql+psycopg2://rag_user:SecureP@ssw0rd@192.168.1.100:5432/rag_db
OPENAI_API_BASE=http://10.0.0.50:8000/v1
OPENAI_API_KEY=sk-internal-key-123456
CHAT_MODEL_NAME=openai/gpt-oss-20b
LLM_API_BASE=http://10.0.0.50:8000/v1
LLM_API_KEY=sk-internal-key-123456
EMBED_API_BASE=http://10.0.0.51:8000/v1
EMBED_API_KEY=sk-embed-key-789012
EMBED_MODEL_NAME=nvidia/nv-embed-v2
DEFAULT_COLLECTION=laws
LOG_LEVEL=INFO
```

---

**文件版本**: 1.0  
**最後更新**: 2025-10-08  
**維護者**: zzw09773
