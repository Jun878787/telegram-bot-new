#!/usr/bin/env python3
"""
服務器啟動腳本 - 同時運行Telegram機器人和Web服務
專為Render平台優化
"""
import os
import sys
import threading
import time
import logging
import traceback
from logging.handlers import RotatingFileHandler

# 配置日誌
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "server.log")

# 創建日誌處理器
handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 獲取日誌對象
logger = logging.getLogger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG') == 'true' else logging.INFO)
logger.addHandler(handler)

# 也添加控制台輸出
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

def start_bot_thread():
    """在單獨的線程中啟動機器人"""
    try:
        logger.info("正在啟動Telegram機器人線程...")
        # 更新機器人狀態
        try:
            from app import set_bot_running
            set_bot_running(True)
        except Exception as e:
            logger.warning(f"無法更新機器人狀態: {str(e)}")
            
        import bot
        bot.run_bot()
    except Exception as e:
        logger.error(f"啟動機器人時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        # 更新機器人狀態
        try:
            from app import set_bot_running
            set_bot_running(False)
        except:
            pass

def start_flask_app():
    """啟動Flask應用程序"""
    try:
        logger.info("正在啟動Flask Web服務...")
        from app import app
        port = int(os.environ.get('PORT', 10000))
        logger.info(f"綁定到端口: {port}")
        app.run(host='0.0.0.0', port=port, threaded=True)
    except Exception as e:
        logger.error(f"啟動Flask應用程序時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

def print_system_info():
    """打印系統信息，有助於調試"""
    try:
        import platform
        import psutil
    except ImportError:
        logger.warning("無法導入 platform 或 psutil 模塊")
        return
        
    logger.info("=== 系統信息 ===")
    logger.info(f"Python 版本: {sys.version}")
    logger.info(f"平台: {platform.platform()}")
    logger.info(f"處理器: {platform.processor()}")
    
    try:
        logger.info(f"CPU 核心: {psutil.cpu_count()}")
        logger.info(f"RAM: {psutil.virtual_memory().total / (1024 * 1024 * 1024):.2f} GB")
        logger.info(f"磁盤空間: {psutil.disk_usage('/').total / (1024 * 1024 * 1024):.2f} GB")
    except:
        logger.warning("無法獲取詳細系統信息")
    
    logger.info("=== 環境變量 ===")
    for key in sorted(os.environ.keys()):
        value = os.environ.get(key)
        # 不記錄敏感信息
        if key in ["BOT_TOKEN", "API_KEY", "SECRET", "PASSWORD", "TOKEN"]:
            value = value[:5] + "..." if value else None
        logger.info(f"{key}: {value}")
        
    logger.info("=== 目錄內容 ===")
    for item in os.listdir('.'):
        if os.path.isdir(item):
            logger.info(f"目錄: {item}/")
        else:
            logger.info(f"文件: {item} ({os.path.getsize(item) / 1024:.2f} KB)")

def check_required_files():
    """檢查必要的文件是否存在"""
    missing_files = []
    for filename in ["app.py", "bot.py"]:
        if not os.path.exists(filename):
            missing_files.append(filename)
            logger.error(f"錯誤: {filename} 不存在!")
    
    if missing_files:
        logger.error(f"缺少必要文件: {', '.join(missing_files)}")
        return False
    return True

def main():
    """主函數"""
    try:
        logger.info("====== 服務器啟動 ======")
        
        # 打印環境信息
        print_system_info()
        
        # 檢查文件
        if not check_required_files():
            sys.exit(1)
            
        # 檢查環境變量
        if not os.environ.get('BOT_TOKEN'):
            logger.warning("警告: 未設置 BOT_TOKEN 環境變量")
        
        # 在後台執行機器人
        bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
        bot_thread.start()
        logger.info("機器人線程已啟動")
        
        # 給機器人一些時間初始化
        time.sleep(2)
        
        # 啟動Flask應用 (這會阻塞直到服務停止)
        start_flask_app()
        
    except Exception as e:
        logger.error(f"服務器啟動失敗: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 