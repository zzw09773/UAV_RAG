#!/bin/bash
# UTF-8 環境設定腳本
# 用於確保內網部署時正確處理中文字元

# 設定系統語言環境為 UTF-8
export LANG=zh_TW.UTF-8
export LC_ALL=zh_TW.UTF-8
export LC_CTYPE=zh_TW.UTF-8

# 設定 Python 使用 UTF-8 編碼
export PYTHONIOENCODING=utf-8

# 設定 PostgreSQL 客戶端編碼
export PGCLIENTENCODING=UTF8

echo "✓ UTF-8 環境變數已設定:"
echo "  LANG=$LANG"
echo "  LC_ALL=$LC_ALL"
echo "  PYTHONIOENCODING=$PYTHONIOENCODING"
echo "  PGCLIENTENCODING=$PGCLIENTENCODING"
