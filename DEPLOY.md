# Render部署指南

## 部署前的準備工作

1. 確保所有必要的檔案都在專案根目錄中：
   - `app.py` - Flask應用程式入口點
   - `bot.py` - Telegram機器人主程式
   - `wsgi.py` - Web服務閘道介面
   - `requirements.txt` - 依賴套件清單
   - `Procfile` - 處理程序設定檔
   - `render.yaml` - Render配置檔
   - `start.py` - 啟動腳本（用於解決gunicorn安裝問題）

2. 確認`render.yaml`和`Procfile`中的啟動命令一致：
   - render.yaml: `startCommand: python start.py`
   - Procfile: `web: python -m gunicorn app:app`

## 部署步驟

1. 登入[Render](https://dashboard.render.com/)

2. 將您的專案連接到GitHub儲存庫
   - 點擊 "New" > "Web Service"
   - 選擇您的GitHub儲存庫
   - 選擇使用 "render.yaml" 進行配置 

3. 設定環境變數
   - 確保設定必要的密鑰，如 `BOT_TOKEN`、`ADMIN_ID` 和 `TARGET_GROUP_ID`

4. 點擊 "Create Web Service" 開始部署

## 故障排除

### 常見問題1: gunicorn命令找不到
如果收到錯誤 `bash: line 1: gunicorn: command not found`：

1. 已通過以下方法修復：
   - 更新 `requirements.txt`，將 gunicorn 放到文件頂部
   - 在 `render.yaml` 中使用 `pip install gunicorn && pip install -r requirements.txt` 確保先安裝gunicorn
   - 創建 `start.py` 啟動腳本，處理依賴安裝並啟動應用
   - 設置 `render.yaml` 使用 `python start.py` 啟動

2. 若仍出現問題，可以嘗試：
   - 在部署設置中檢查日誌，查看確切錯誤
   - 確認您的Python版本與依賴兼容（Render預設使用Python 3.7）
   - 嘗試使用不同的WSGI服務器，如 `waitress`

### 常見問題2: 找不到app.py
如果收到錯誤 `python: can't open file '/opt/render/project/src/app.py': [Errno 2] No such file or directory`：

1. 檢查 app.py 是否在專案根目錄中
2. 確認 render.yaml 中 rootDir 設定為 "."
3. 確保 startCommand 使用正確的路徑
4. 先前已通過啟用 `start.py` 腳本解決，它會檢查app.py是否存在

### 其他常見問題解決方法

- **找不到模組錯誤**：確保所有依賴都列在 requirements.txt 中
- **權限錯誤**：檢查資料目錄的權限設定
- **日誌錯誤**：確保日誌目錄存在且可寫入

## 推薦配置

在 `requirements.txt` 中添加以下關鍵依賴：
```
gunicorn==21.2.0
flask>=2.0.0
python-telegram-bot>=13.0
```

使用啟動腳本運行應用：
```yaml
services:
  - type: web
    name: telegram-bot
    runtime: python
    buildCommand: pip install gunicorn && pip install -r requirements.txt
    startCommand: python start.py
    rootDir: .
```

## 部署後檢查

1. 訪問Render提供的URL確認服務是否正常運行
2. 檢查Render日誌，確保沒有錯誤
3. 若應用啟動但機器人無響應，確認Telegram Webhook設置或輪詢機制 