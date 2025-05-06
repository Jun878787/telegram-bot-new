# Render部署指南

## 部署前的準備工作

1. 確保所有必要的檔案都在專案根目錄中：
   - `app.py` - Flask應用程式入口點
   - `bot.py` - Telegram機器人主程式
   - `wsgi.py` - Web服務閘道介面
   - `requirements.txt` - 依賴套件清單
   - `Procfile` - 處理程序設定檔
   - `render.yaml` - Render配置檔

2. 確認`render.yaml`和`Procfile`中的啟動命令一致：
   - render.yaml: `startCommand: python app.py`
   - Procfile: `web: python app.py`

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

如果收到錯誤 `python: can't open file '/opt/render/project/src/app.py': [Errno 2] No such file or directory`：

1. 檢查 app.py 是否在專案根目錄中
2. 確認 render.yaml 中 rootDir 設定為 "."
3. 確保 startCommand 使用正確的路徑：`python app.py`
4. 嘗試變更啟動命令為：`gunicorn app:app`（需在requirements.txt中添加gunicorn）

### 其他常見問題解決方法

- **找不到模組錯誤**：確保所有依賴都列在 requirements.txt 中
- **權限錯誤**：檢查資料目錄的權限設定
- **日誌錯誤**：確保日誌目錄存在且可寫入

## 推薦配置

在 `requirements.txt` 中添加以下關鍵依賴：
```
flask>=2.0.0
gunicorn>=20.1.0
python-telegram-bot>=13.0
```

修改 `render.yaml` 使用gunicorn運行應用：
```yaml
services:
  - type: web
    name: telegram-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    rootDir: .
``` 