import os
import threading
import time
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Telegram Bot is running!'

@app.route('/health')
def health():
    return 'OK'

# 機器人啟動線程
def start_bot():
    import bot
    bot.run_bot()

if __name__ == '__main__':
    # 在背景執行機器人
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # 獲取 Render 分配的端口
    port = int(os.environ.get('PORT', 10000))
    
    # 執行 Flask 應用
    app.run(host='0.0.0.0', port=port) 