# Telegram 群組管理與記帳機器人

這是一個功能豐富的Telegram機器人，提供群組管理和記帳功能，適合團隊、企業或社群使用。

## 功能特點

- **記帳功能**：
  - 台幣(TW)和人民幣(CNY)記帳
  - 個人和總表報表生成
  - 支持歷史記錄查詢
  - 資金追蹤

- **群組管理**：
  - 成員管理（踢出/封禁/解除封禁）
  - 消息刪除（單條/批量）
  - 歡迎新成員自動提示
  - 警告系統

- **管理員功能**：
  - 操作員設定
  - 權限管理
  - 群組設定調整

## 安裝與設置

### 先決條件

- Python 3.8+
- Telegram Bot API Token（從 [BotFather](https://t.me/botfather) 獲取）

### 安裝步驟

1. 克隆此專案
   ```bash
   git clone https://github.com/yourusername/telegram-bot.git
   cd telegram-bot
   ```

2. 安裝依賴項
   ```bash
   pip install -r requirements.txt
   ```

3. 設置配置文件：
   - 複製 `config.example.json` 為 `config.json`
   - 複製 `bot_config.example.json` 為 `bot_config.json`
   - 複製 `env.example` 為 `.env`
   - 根據需要修改配置文件

4. 在 `.env` 中設置您的 Bot Token 和其他必要參數

5. 創建數據存儲目錄
   ```bash
   mkdir data logs
   ```

6. 運行機器人
   ```bash
   python bot.py
   ```

## 配置

### .env

包含機器人的主要配置項：
- Bot Token
- 管理員 ID
- 群組 ID
- 日誌設定等

### config.json

包含機器人的運行時配置：
- 匯率設定
- 歡迎訊息
- 操作員列表
- 定時訊息設定

### bot_config.json

包含機器人的交易記錄配置：
- 交易記錄
- 匯率
- 操作員

## 使用指南

### 基本指令

| 指令 | 描述 |
|------|------|
| `/start` | 啟動機器人 |
| `💰TW` | 台幣記帳 |
| `💰CN` | 人民幣記帳 |
| `📊查看本月報表` | 查看個人本月報表 |
| `📚歷史報表` | 查看歷史報表 |
| `總表` | 查看總表 |
| `總表資金` | 查看總表資金狀態 |

### 記帳格式

- `TW+1000` - 新增1000台幣
- `CN-500` - 減少500人民幣
- `05/06 TW+340000` - 在特定日期新增台幣
- `設置今日匯率4.5` - 設置今日匯率
- `設置"2023-12-25"匯率4.4` - 設置特定日期匯率

### 管理員指令

| 指令 | 描述 |
|------|------|
| `⚙️群管設定` | 進入群組管理設定 |
| `🧹 清理訊息` | 清理訊息選項 |
| `刪除所有聊天室訊息` | 刪除所有訊息 |
| `刪除所有非置頂訊息` | 僅保留置頂訊息 |
| `/ban @用戶名` | 封禁用戶 |
| `/unban @用戶名` | 解除封禁 |
| `/kick @用戶名` | 踢出用戶 |
| `/warn @用戶名` | 警告用戶 |

## 部署

### 本地部署

按照上述安裝步驟操作即可在本地環境運行。

### Render 部署

1. Fork 此專案到您的 GitHub 帳號

2. 在 Render 網站上創建新的 Web Service
   - 連接到您的 GitHub 專案
   - 選擇 `Python` 環境
   - 建構命令: `pip install -r requirements.txt`
   - 啟動命令: `python bot.py`

3. 在 Render 的環境變數中設置：
   - `BOT_TOKEN`: 您的 Telegram Bot Token
   - `ADMIN_ID`: 管理員的 Telegram ID
   - `TARGET_GROUP_ID`: 目標群組 ID

4. 添加持久化儲存配置
   - Render 平台會自動使用 `render.yaml` 中的磁碟配置
   - 所有數據將存儲在 `/data` 目錄

## 故障排除

常見問題及解決方案：

1. **機器人無法回應**：
   - 檢查 Bot Token 是否正確
   - 確認機器人在目標群組中有管理員權限

2. **記帳功能不正常**：
   - 確認 JSON 數據文件是否可寫
   - 檢查機器人的錯誤日誌

3. **權限問題**：
   - 確認機器人在群組中的權限設置
   - 檢查管理員 ID 是否正確設置

## 貢獻

歡迎提交 Pull Requests 或創建 Issues 來改進此專案。

## 許可證

此專案採用 MIT 許可證。 