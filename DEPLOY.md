# Telegram 機器人部署指南

本文檔提供在 Render 平台上部署 Telegram 機器人的詳細指南。

## 部署架構

此 Telegram 機器人部署採用以下架構：

1. **主要啟動腳本**: `server.py` - 同時啟動 Telegram 機器人和 Web 服務
2. **機器人邏輯**: `bot.py` - 包含 Telegram 機器人的核心功能
3. **Web 服務**: `app.py` - 提供健康檢查和狀態監控的 Flask 應用

這種架構確保機器人始終運行，並且 Render 平台可以通過 Web 服務監控機器人狀態。

## 文件說明

- **server.py**: 主啟動腳本，負責配置日誌、啟動機器人和 Web 服務
- **app.py**: Flask Web 應用，提供健康檢查和狀態監視功能
- **bot.py**: Telegram 機器人的核心邏輯
- **wsgi.py**: 用於 gunicorn 啟動 Flask 應用
- **requirements.txt**: 依賴項列表
- **render.yaml**: Render 部署配置
- **Procfile**: 用於定義啟動命令

## 環境變量

在 Render 上部署時，需要設置以下環境變量：

- `BOT_TOKEN`: Telegram 機器人的 API 令牌
- `ADMIN_ID`: 管理員的 Telegram ID
- `TARGET_GROUP_ID`: 目標群組的 Telegram ID
- `PORT`: Web 服務的端口號（Render 會自動設置）
- `DEBUG`: 設置為 "true" 啟用調試日誌
- `RENDER`: 設置為 "true" 表示在 Render 環境中運行

## 部署步驟

1. **創建 Render 服務**:
   - 登錄到 Render 控制台
   - 點擊 "New" 並選擇 "Web Service"
   - 連接到您的 GitHub 倉庫

2. **配置服務**:
   - 名稱: `telegram-bot`（或您喜歡的任何名稱）
   - 環境: `Python`
   - 構建命令: `pip install gunicorn && pip install -r requirements.txt`
   - 啟動命令: `python server.py`
   - 設置所有所需的環境變量

3. **添加持久存儲**:
   - 在 Render 控制台中為您的服務添加磁盤
   - 設置掛載路徑為 `/data`
   - 分配至少 1 GB 空間

## 故障排查

如果您在部署過程中遇到問題，請檢查：

1. **日誌檢查**: 
   - 在 Render 控制台中查看日誌以獲取詳細錯誤信息

2. **常見問題**:
   - **端口綁定問題**: 確保在 `server.py` 和 `app.py` 中使用環境變量 `PORT`
   - **模塊未找到**: 確保所有依賴項都在 `requirements.txt` 中列出
   - **機器人令牌無效**: 檢查 `BOT_TOKEN` 環境變量是否正確設置

3. **訪問 Web 服務**:
   - 通過 Render 分配的域名訪問 Web 服務（例如，`https://your-app-name.onrender.com/`）
   - 檢查 `/health` 端點是否返回 "OK"
   - 訪問 `/status` 獲取詳細的系統狀態

## 重要注意事項

- 所有敏感數據（如 BOT_TOKEN）應通過環境變量提供，而不是硬編碼在源代碼中
- 機器人會在 Web 服務啟動時自動在後台運行
- 對於生產環境，建議將 `DEBUG` 環境變量設置為 "false"

如果需要進一步幫助，請參考 Render 的官方文檔或提交問題到專案的 GitHub 倉庫。 