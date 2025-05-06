import os
import json
import threading
import time
import datetime
import logging
from flask import Flask, jsonify, request

app = Flask(__name__)
logger = logging.getLogger(__name__)

# 服務器狀態變量
SERVICE_STATUS = {
    "start_time": datetime.datetime.now().isoformat(),
    "is_bot_running": False,
    "requests_served": 0,
    "last_request": None,
    "errors": 0
}

@app.route('/')
def home():
    """主頁 - 顯示基本信息"""
    SERVICE_STATUS["requests_served"] += 1
    SERVICE_STATUS["last_request"] = datetime.datetime.now().isoformat()
    
    uptime = datetime.datetime.now() - datetime.datetime.fromisoformat(SERVICE_STATUS["start_time"])
    uptime_str = f"{uptime.days}天 {uptime.seconds // 3600}小時 {(uptime.seconds // 60) % 60}分鐘"
    
    return jsonify({
        "status": "運行中",
        "service": "Telegram 機器人",
        "uptime": uptime_str,
        "bot_status": "運行中" if SERVICE_STATUS["is_bot_running"] else "未運行",
        "port": os.environ.get("PORT", "10000"),
        "environment": "Render" if os.environ.get("RENDER") else "本地",
        "requests_served": SERVICE_STATUS["requests_served"]
    })

@app.route('/health')
def health():
    """健康檢查端點 - 供 Render 檢測服務狀態"""
    SERVICE_STATUS["requests_served"] += 1
    SERVICE_STATUS["last_request"] = datetime.datetime.now().isoformat()
    return jsonify({"status": "OK", "timestamp": datetime.datetime.now().isoformat()})

@app.route('/status')
def status():
    """詳細狀態信息"""
    SERVICE_STATUS["requests_served"] += 1
    SERVICE_STATUS["last_request"] = datetime.datetime.now().isoformat()
    
    # 獲取系統信息
    system_info = {
        "python_version": os.sys.version,
        "platform": os.sys.platform,
        "environment_variables": {k: "[hidden]" if k in ["BOT_TOKEN", "API_KEY"] else v 
                                for k, v in dict(os.environ).items()}
    }
    
    # 返回所有狀態信息
    return jsonify({
        "service_status": SERVICE_STATUS,
        "system_info": system_info
    })

def set_bot_running(status=True):
    """設置機器人運行狀態"""
    SERVICE_STATUS["is_bot_running"] = status

if __name__ == '__main__':
    # 在背景執行機器人
    try:
        from bot import run_bot
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        set_bot_running(True)
        logger.info("機器人線程已啟動")
    except Exception as e:
        logger.error(f"啟動機器人時出錯: {str(e)}")
        SERVICE_STATUS["errors"] += 1
    
    # 獲取 Render 分配的端口
    port = int(os.environ.get('PORT', 10000))
    
    # 執行 Flask 應用
    app.run(host='0.0.0.0', port=port) 