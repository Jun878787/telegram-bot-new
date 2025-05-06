import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from datetime import datetime, timedelta
import os
import sys
import logging
import json
import re
import threading
import platform
import signal
import subprocess
import psutil
import time
import http.server
import socketserver
from functools import wraps

# 全局變量
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
DATA_FILE = 'data/accounting.json'
EXCHANGE_RATES_FILE = 'data/exchange_rates.json'
USER_SETTINGS_FILE = 'data/user_settings.json'
BOT_CONFIG_FILE = 'bot_config.json'
CONFIG_FILE = 'config.json'
LOG_FILE = 'logs/bot.log'
MAX_ERROR_COUNT = 5
RESTART_FLAG = False
BOT_START_TIME = datetime.now()

# 初始化機器人
bot = telebot.TeleBot(BOT_TOKEN)

# 用戶狀態字典
user_states = {}
error_count = 0
error_time = datetime.now()

# 檢查是否為管理員
def is_admin(user_id, chat_id=None, check_operator=True):
    """檢查用戶是否為管理員或操作員"""
    str_user_id = str(user_id)
    
    try:
        # 檢查機器人設定文件中的操作員
        if check_operator:
            try:
                with open(BOT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                operators = config.get('operators', [])
                if str_user_id in [str(op) for op in operators]:
                    return True
            except Exception as e:
                logger.error(f"讀取操作員設定失敗: {e}")
        
        # 如果不是操作員，檢查Telegram群組管理員
        if chat_id:
            try:
                chat_member = bot.get_chat_member(chat_id, user_id)
                if chat_member.status in ['creator', 'administrator']:
                    return True
            except Exception as e:
                logger.error(f"獲取聊天成員信息失敗: {e}")
        
        # 檢查機器人管理員
        admins = get_admin_ids()
        return str_user_id in [str(admin) for admin in admins]
    except Exception as e:
        logger.error(f"檢查管理員權限時錯誤: {e}")
        return False

# 機器人啟動通知
def send_startup_notification():
    """向管理員發送機器人啟動通知"""
    admins = get_admin_ids()
    startup_message = f"""🤖 <b>機器人已啟動</b>

<b>啟動時間:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>Python版本:</b> {platform.python_version()}
<b>系統平台:</b> {platform.system()} {platform.release()}
    
<b>狀態:</b> 正常運行中...
"""
    
    for admin_id in admins:
        try:
            bot.send_message(admin_id, startup_message, parse_mode='HTML')
            logger.info(f"已向管理員 {admin_id} 發送啟動通知")
        except Exception as e:
            logger.error(f"無法向管理員 {admin_id} 發送啟動通知: {e}")

# 日誌設置
def setup_logging():
    """設置日誌記錄器"""
    global logger
    
    # 確保日誌目錄存在
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    logger = logging.getLogger('bot_logger')
    logger.setLevel(logging.INFO)
    
    # 文件處理器
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加處理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 初始化數據文件
def init_files():
    """初始化必要的數據文件"""
    # 確保數據目錄存在
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    
    # 初始化會計數據文件
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        logger.info(f"創建了會計數據文件: {DATA_FILE}")
    
    # 初始化匯率數據文件
    if not os.path.exists(EXCHANGE_RATES_FILE):
        with open(EXCHANGE_RATES_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        logger.info(f"創建了匯率數據文件: {EXCHANGE_RATES_FILE}")
    
    # 初始化用戶設置文件
    if not os.path.exists(USER_SETTINGS_FILE):
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        logger.info(f"創建了用戶設置文件: {USER_SETTINGS_FILE}")

# 數據加載函數
def load_data(file_path):
    """從JSON文件加載數據"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加載數據文件失敗 {file_path}: {e}")
        return {}

# 數據保存函數
def save_data(data, file_path):
    """保存數據到JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"保存數據文件失敗 {file_path}: {e}")

# 獲取報表名稱
def get_report_name(user_id):
    """獲取用戶報表名稱設定"""
    settings = load_data(USER_SETTINGS_FILE)
    return settings.get(str(user_id), {}).get('report_name', '個人報表')

# 設置報表名稱
def set_report_name(user_id, name):
    """設置用戶報表名稱"""
    settings = load_data(USER_SETTINGS_FILE)
    str_user_id = str(user_id)
    if str_user_id not in settings:
        settings[str_user_id] = {}
    settings[str_user_id]['report_name'] = name
    save_data(settings, USER_SETTINGS_FILE)
    return True

# 獲取當前匯率
def get_rate(date=None):
    """獲取指定日期的匯率，默認為今天"""
    date = date or datetime.now().strftime('%Y-%m-%d')
    rates = load_data(EXCHANGE_RATES_FILE)
    return rates.get(date, rates.get(max(rates.keys())) if rates else 29)

# 設置匯率
def set_rate(rate, date=None):
    """設置指定日期的匯率，默認為今天"""
    date = date or datetime.now().strftime('%Y-%m-%d')
    rates = load_data(EXCHANGE_RATES_FILE)
    rates[date] = rate
    save_data(rates, EXCHANGE_RATES_FILE)
    return True

# 新增交易記錄
def add_transaction(user_id, date, type_currency, amount):
    """添加交易記錄"""
    data = load_data(DATA_FILE)
    str_user_id = str(user_id)
    if str_user_id not in data:
        data[str_user_id] = {}
    if date not in data[str_user_id]:
        data[str_user_id][date] = {}
    if type_currency not in data[str_user_id][date]:
        data[str_user_id][date][type_currency] = 0
    data[str_user_id][date][type_currency] += amount
    save_data(data, DATA_FILE)
    return True

# 刪除交易記錄
def delete_transaction(user_id, date, currency):
    """刪除指定日期的特定貨幣交易記錄"""
    data = load_data(DATA_FILE)
    str_user_id = str(user_id)
    if str_user_id in data and date in data[str_user_id]:
        if currency in data[str_user_id][date]:
            del data[str_user_id][date][currency]
            if not data[str_user_id][date]:  # 如果日期下沒有其他貨幣記錄，刪除該日期
                del data[str_user_id][date]
            save_data(data, DATA_FILE)
            return True
    return False

# 更新資金
def update_fund(fund_type, amount):
    """更新資金額度"""
    config = load_data(BOT_CONFIG_FILE)
    if 'funds' not in config:
        config['funds'] = {}
    if fund_type not in config['funds']:
        config['funds'][fund_type] = 0
    config['funds'][fund_type] += amount
    save_data(config, BOT_CONFIG_FILE)
    return True

# 解析日期字符串
def parse_date(date_str):
    """解析各種格式的日期字符串"""
    try:
        # 嘗試解析 YYYY-MM-DD 格式
        if re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
            return datetime.strptime(date_str, '%Y-%m-%d')
        # 嘗試解析 MM/DD 格式
        elif re.match(r'\d{1,2}/\d{1,2}', date_str):
            today = datetime.now()
            month, day = map(int, date_str.split('/'))
            return datetime(today.year, month, day)
        # 嘗試解析其他可能的格式
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        # 如果解析失敗，返回今天的日期
        return datetime.now()

# 生成報表
def generate_report(user_id, month=None, year=None):
    """生成用戶的月度報表"""
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    
    # 獲取該月的第一天和最後一天
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # 加載用戶數據
    data = load_data(DATA_FILE)
    str_user_id = str(user_id)
    user_data = data.get(str_user_id, {})
    
    # 加載資金數據
    config = load_data(BOT_CONFIG_FILE)
    funds = config.get('funds', {})
    
    # 計算月份總額
    tw_total = 0
    cn_total = 0
    report_lines = []
    
    # 遍歷該月每一天
    current_date = first_day
    while current_date <= last_day:
        date = current_date.strftime('%Y-%m-%d')
        dt = current_date
        day_str = dt.strftime('%m/%d')
        weekday = dt.weekday()
        weekday_str = ('一', '二', '三', '四', '五', '六', '日')[weekday]
        
        day_data = user_data.get(date, {"TW": 0, "CN": 0})
        tw_amount = day_data.get("TW", 0)
        cn_amount = day_data.get("CN", 0)
        
        tw_total += tw_amount
        cn_total += cn_amount
        
        # 只有在有金額或是第1天/15日/末日時才顯示
        if tw_amount != 0 or cn_amount != 0 or dt.day == 1 or dt.day == 15 or dt.day == last_day:
            tw_display = f"{tw_amount:,.0f}" if tw_amount else "0"
            cn_display = f"{cn_amount:,.0f}" if cn_amount else "0"
        
            # 使用表格式格式，簡潔清晰
            line = f"<code>{day_str}({weekday_str})</code> "
            
            # 只有在有金額時才顯示金額
            if tw_amount != 0 or cn_amount != 0:
                if tw_amount != 0:
                    line += f"<code>NT${tw_display}</code> "
                if cn_amount != 0:
                    line += f"<code>CN¥{cn_display}</code>"
            
            report_lines.append(line.strip())
        
        # 每週末或月末添加分隔線
        if weekday == 6 or dt.day == last_day:
            report_lines.append("－－－－－－－－－－")
        
        current_date += timedelta(days=1)
    
    # 更新 USDT 換算公式 - 乘以 0.01 (1%)
    tw_rate = get_rate()
    cn_rate = 4.75  # 人民幣固定匯率
    
    # 新的計算公式: 金額/匯率*0.01
    tw_usdt = (tw_total / tw_rate) * 0.01 if tw_rate else 0
    cn_usdt = (cn_total / cn_rate) * 0.01 if cn_rate else 0
    
    report_name = get_report_name(user_id)
    
    # 格式化數字
    tw_total_display = f"{tw_total:,.0f}"
    tw_usdt_display = f"{tw_usdt:.2f}"
    cn_total_display = f"{cn_total:,.0f}"
    cn_usdt_display = f"{cn_usdt:.2f}"
    
    # 公桶和私人資金顯示為整數
    public_funds = funds.get('public', 0)
    private_funds = funds.get('private', 0)
    public_funds_display = f"{public_funds:.0f}"
    private_funds_display = f"{private_funds:.0f}"
    
    # 報表頭部更新 - 使用更清晰的格式
    header = [
        f"<b>【{report_name}】</b>",
        f"<b>◉ 台幣業績</b>",
        f"<code>NT${tw_total_display}</code> → <code>USDT${tw_usdt_display}</code>",
        f"<b>◉ 人民幣業績</b>",
        f"<code>CN¥{cn_total_display}</code> → <code>USDT${cn_usdt_display}</code>",
        f"<b>◉ 資金狀態</b>",
        f"公桶: <code>USDT${public_funds_display}</code>",
        f"私人: <code>USDT${private_funds_display}</code>",
        "－－－－－－－－－－",
        f"<b>{year}年{month}月收支明細</b>"
    ]
    
    return "\n".join(header + report_lines)

# 處理初始化確認
@bot.message_handler(func=lambda message: message.reply_to_message is not None and 
                                          message.from_user.id in user_states and 
                                          user_states[message.from_user.id].get('state') == 'waiting_init_confirmation' and
                                          user_states[message.from_user.id].get('prompt_msg_id') == message.reply_to_message.message_id)
@error_handler
def handle_init_confirmation(message):
    """處理用戶對初始化報表的確認"""
    user_id = message.from_user.id
    str_user_id = str(user_id)
    
    # 記錄用戶的回覆，便於調試
    logger.info(f"收到用戶 {message.from_user.username or user_id} 的初始化確認回覆: '{message.text}'")
    
    try:
        if message.text == "確認初始化":
            # 從數據中移除用戶資料
            data = load_data(DATA_FILE)
            logger.info(f"嘗試初始化用戶 {str_user_id} 的報表數據")
            
            if str_user_id in data:
                data[str_user_id] = {}
                save_data(data, DATA_FILE)
                logger.info(f"已清空用戶 {str_user_id} 的報表數據")
            else:
                logger.info(f"用戶 {str_user_id} 在數據文件中沒有記錄")
            
            # 重置報表名稱
            settings = load_data(USER_SETTINGS_FILE)
            if str_user_id in settings:
                if 'report_name' in settings[str_user_id]:
                    settings[str_user_id]['report_name'] = "總表"
                save_data(settings, USER_SETTINGS_FILE)
                logger.info(f"已重置用戶 {str_user_id} 的報表名稱")
            
            bot.reply_to(message, "✅ 報表已成功初始化！所有記帳數據已清空。")
            logger.info(f"用戶 {message.from_user.username or user_id} 已初始化報表")
        else:
            bot.reply_to(message, "❌ 初始化已取消。")
            logger.info(f"用戶 {message.from_user.username or user_id} 取消了初始化報表")
    except Exception as e:
        error_msg = f"初始化報表時出錯: {str(e)}"
        logger.error(error_msg)
        bot.reply_to(message, f"❌ 初始化報表時出錯: {str(e)}")
    finally:
        # 確保無論如何都清除用戶狀態
        if user_id in user_states:
            del user_states[user_id]
            logger.info(f"已清除用戶 {user_id} 的狀態") 