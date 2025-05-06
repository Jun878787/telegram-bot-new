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
import traceback

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

# 錯誤處理裝飾器
def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 獲取全局錯誤計數器
            global error_count, error_time
            
            # 記錄錯誤
            error_msg = f"機器人錯誤: {str(e)}"
            exc_info = sys.exc_info()
            if exc_info[2]:
                line_number = exc_info[2].tb_lineno
                error_msg += f" (行: {line_number})"
            
            # 只有在有logger時才記錄
            if 'logger' in globals():
                logger.error(error_msg)
                logger.error(f"詳細錯誤: {repr(e)}")
            else:
                print(error_msg)
                print(f"詳細錯誤: {repr(e)}")
            
            # 計算錯誤率
            now = datetime.now()
            if (now - error_time).total_seconds() > 3600:  # 1小時重置計數器
                error_count = 0
                error_time = now
            
            error_count += 1
            
            # 檢查是否需要重啟
            if error_count > int(os.environ.get('MAX_ERROR_COUNT', MAX_ERROR_COUNT)):
                if 'logger' in globals():
                    logger.critical(f"錯誤次數過多 ({error_count})，標記機器人需要重啟")
                else:
                    print(f"錯誤次數過多 ({error_count})，標記機器人需要重啟")
                
                global RESTART_FLAG
                RESTART_FLAG = True
            
            # 如果是消息處理器，嘗試回復錯誤
            try:
                if len(args) > 0 and hasattr(args[0], 'chat') and hasattr(args[0], 'from_user'):
                    message = args[0]
                    bot.reply_to(message, f"❌ 發生錯誤: {str(e)}\n請稍後重試或聯繫管理員。")
            except:
                pass
                
    return wrapper

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

# 獲取管理員ID列表
def get_admin_ids():
    """獲取管理員ID列表"""
    admin_id = os.environ.get('ADMIN_ID')
    if admin_id:
        # 處理可能的多個管理員ID
        if ',' in admin_id:
            return [int(aid.strip()) for aid in admin_id.split(',')]
        return [int(admin_id)]
    return []

# 處理 /start 命令
@bot.message_handler(commands=['start'])
@error_handler
def handle_start(message):
    """處理 /start 命令，顯示主選單"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # 歡迎訊息
    welcome_text = f"""👋 <b>歡迎使用交易記錄機器人！</b>

您可以使用此機器人來記錄和查詢各種交易。
請點擊下方按鈕開始操作："""

    # 創建主選單按鈕
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # 添加功能按鈕
    keyboard.add(
        InlineKeyboardButton("📊 查看報表", callback_data="report_view"),
        InlineKeyboardButton("💰 台幣入帳", callback_data="add_tw"),
        InlineKeyboardButton("💴 人民幣入帳", callback_data="add_cn"),
        InlineKeyboardButton("📆 設定匯率", callback_data="set_rate"),
        InlineKeyboardButton("⚙️ 設定", callback_data="settings"),
        InlineKeyboardButton("❓ 幫助", callback_data="help")
    )
    
    # 僅對管理員顯示管理選項
    if is_admin(user_id, chat_id):
        keyboard.add(
            InlineKeyboardButton("🔄 初始化報表", callback_data="report_init"),
            InlineKeyboardButton("👥 管理操作員", callback_data="manage_operators")
        )
    
    # 發送選單
    bot.send_message(chat_id, welcome_text, reply_markup=keyboard, parse_mode='HTML')
    
    if 'logger' in globals():
        logger.info(f"用戶 {message.from_user.username or user_id} 啟動了機器人")

# 處理 /menu 命令
@bot.message_handler(commands=['menu'])
@error_handler
def handle_menu(message):
    """處理 /menu 命令，顯示主選單"""
    handle_start(message)  # 使用相同的選單

# 處理按鈕回調
@bot.callback_query_handler(func=lambda call: True)
@error_handler
def handle_button_click(call):
    """處理按鈕點擊事件"""
    try:
        # 獲取回調數據
        callback_data = call.data
        user_id = call.from_user.id
        
        # 記錄回調事件
        if 'logger' in globals():
            logger.info(f"收到用戶 {call.from_user.username or user_id} 的按鈕點擊: '{callback_data}'")
        
        # 處理主選單按鈕
        if callback_data == "report_view":
            # 查看報表 - 顯示本月報表
            report = generate_report(user_id)
            
            # 添加月份選擇按鈕
            now = datetime.now()
            keyboard = InlineKeyboardMarkup(row_width=3)
            
            # 添加最近3個月的按鈕
            month_buttons = []
            for i in range(3):
                month = now.month - i
                year = now.year
                if month <= 0:
                    month += 12
                    year -= 1
                month_name = ('一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二')[month-1]
                month_buttons.append(
                    InlineKeyboardButton(
                        f"{year}年{month}月",
                        callback_data=f"report_month_{month}_{year}"
                    )
                )
            
            keyboard.add(*month_buttons)
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            
            bot.send_message(call.message.chat.id, report, reply_markup=keyboard, parse_mode='HTML')
            
        elif callback_data == "add_tw":
            # 台幣入帳 - 啟動輸入台幣金額的流程
            msg = bot.send_message(call.message.chat.id, 
                "請輸入台幣入帳金額和日期(選填)，格式如下：\n\n<code>50000 5/1</code>\n\n日期格式可以是MM/DD或YYYY-MM-DD。如不輸入日期，默認為今天。", 
                parse_mode='HTML')
            
            # 設置用戶狀態為等待台幣輸入
            user_states[user_id] = {
                'state': 'waiting_tw_input',
                'prompt_msg_id': msg.message_id
            }
            
        elif callback_data == "add_cn":
            # 人民幣入帳 - 啟動輸入人民幣金額的流程
            msg = bot.send_message(call.message.chat.id, 
                "請輸入人民幣入帳金額和日期(選填)，格式如下：\n\n<code>10000 5/1</code>\n\n日期格式可以是MM/DD或YYYY-MM-DD。如不輸入日期，默認為今天。", 
                parse_mode='HTML')
            
            # 設置用戶狀態為等待人民幣輸入
            user_states[user_id] = {
                'state': 'waiting_cn_input',
                'prompt_msg_id': msg.message_id
            }
            
        elif callback_data == "set_rate":
            # 設定匯率 - 僅限管理員
            if not is_admin(user_id, call.message.chat.id):
                bot.answer_callback_query(call.id, "您沒有權限設定匯率")
                return
                
            current_rate = get_rate()
            msg = bot.send_message(call.message.chat.id, 
                f"當前台幣匯率: {current_rate}\n\n請輸入新的匯率，例如: <code>33.5</code>", 
                parse_mode='HTML')
            
            # 設置用戶狀態為等待匯率輸入
            user_states[user_id] = {
                'state': 'waiting_rate_input',
                'prompt_msg_id': msg.message_id
            }
            
        elif callback_data == "settings":
            # 設定選單
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("⌨️ 設定報表名稱", callback_data="set_report_name"),
                InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu")
            )
            
            bot.send_message(call.message.chat.id, "⚙️ 請選擇設定項目：", reply_markup=keyboard)
            
        elif callback_data == "help":
            # 顯示幫助訊息
            help_text = """❓ <b>機器人使用幫助</b>

<b>基本命令：</b>
/start - 啟動機器人並顯示主選單
/menu - 顯示主選單
/report - 查看當月報表

<b>功能說明：</b>
• 查看報表：顯示當月或選定月份的交易報表
• 台幣入帳：記錄台幣交易，格式為 <金額> <日期(選填)>
• 人民幣入帳：記錄人民幣交易，格式同上
• 設定匯率：設定台幣兌換匯率
• 設定：更改報表名稱等個人設定

<b>管理員功能：</b>
• 初始化報表：清空所有交易記錄
• 管理操作員：添加或移除操作員權限
"""
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            
            bot.send_message(call.message.chat.id, help_text, reply_markup=keyboard, parse_mode='HTML')
            
        elif callback_data.startswith('report_'):
            # 處理報表相關按鈕
            parts = callback_data.split('_')
            if len(parts) >= 2:
                action = parts[1]
                
                if action == 'month':
                    # 顯示月報表
                    month = int(parts[2]) if len(parts) > 2 else datetime.now().month
                    year = int(parts[3]) if len(parts) > 3 else datetime.now().year
                    report = generate_report(user_id, month, year)
                    
                    # 創建月份選擇按鈕
                    keyboard = InlineKeyboardMarkup(row_width=3)
                    
                    # 添加上一個月和下一個月按鈕
                    prev_month = month - 1
                    prev_year = year
                    if prev_month <= 0:
                        prev_month += 12
                        prev_year -= 1
                        
                    next_month = month + 1
                    next_year = year
                    if next_month > 12:
                        next_month -= 12
                        next_year += 1
                    
                    keyboard.row(
                        InlineKeyboardButton(f"◀️ {prev_month}月", callback_data=f"report_month_{prev_month}_{prev_year}"),
                        InlineKeyboardButton("🔙 主選單", callback_data="back_to_menu"),
                        InlineKeyboardButton(f"{next_month}月 ▶️", callback_data=f"report_month_{next_month}_{next_year}")
                    )
                    
                    bot.edit_message_text(chat_id=call.message.chat.id, 
                                         message_id=call.message.message_id,
                                         text=report,
                                         parse_mode='HTML',
                                         reply_markup=keyboard)
                    
                elif action == 'init':
                    # 初始化報表確認
                    if not is_admin(user_id, call.message.chat.id):
                        bot.answer_callback_query(call.id, "您沒有權限初始化報表")
                        return
                        
                    kb = InlineKeyboardMarkup()
                    kb.row(
                        InlineKeyboardButton("✅ 確認", callback_data="confirm_init"),
                        InlineKeyboardButton("❌ 取消", callback_data="cancel_init")
                    )
                    bot.edit_message_text(chat_id=call.message.chat.id,
                                         message_id=call.message.message_id,
                                         text="⚠️ 確定要初始化報表嗎？這將清空所有記帳數據！",
                                         reply_markup=kb)
        
        elif callback_data == "set_report_name":
            # 設定報表名稱
            current_name = get_report_name(user_id)
            msg = bot.send_message(call.message.chat.id, 
                f"當前報表名稱: {current_name}\n\n請輸入新的報表名稱：", 
                parse_mode='HTML')
            
            # 設置用戶狀態為等待報表名稱輸入
            user_states[user_id] = {
                'state': 'waiting_report_name',
                'prompt_msg_id': msg.message_id
            }
            
        elif callback_data == "back_to_menu":
            # 返回主選單
            handle_start(call.message)
            
            # 嘗試刪除原訊息
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
                
        elif callback_data == "confirm_init":
            # 確認初始化報表
            if not is_admin(user_id, call.message.chat.id):
                bot.answer_callback_query(call.id, "您沒有權限初始化報表")
                return
                
            data = load_data(DATA_FILE)
            str_user_id = str(user_id)
            
            if str_user_id in data:
                data[str_user_id] = {}
                save_data(data, DATA_FILE)
                logger.info(f"已清空用戶 {str_user_id} 的報表數據")
            
            # 重置報表名稱
            settings = load_data(USER_SETTINGS_FILE)
            if str_user_id in settings:
                if 'report_name' in settings[str_user_id]:
                    settings[str_user_id]['report_name'] = "總表"
                save_data(settings, USER_SETTINGS_FILE)
            
            # 創建返回按鈕
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            
            bot.edit_message_text(chat_id=call.message.chat.id,
                                 message_id=call.message.message_id,
                                 text="✅ 報表已成功初始化！所有記帳數據已清空。",
                                 reply_markup=keyboard)
            
        elif callback_data == "cancel_init":
            # 取消初始化
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            
            bot.edit_message_text(chat_id=call.message.chat.id,
                                 message_id=call.message.message_id,
                                 text="❌ 初始化已取消。",
                                 reply_markup=keyboard)
        
        elif callback_data == "manage_operators":
            # 管理操作員 - 僅限管理員
            if not is_admin(user_id, call.message.chat.id):
                bot.answer_callback_query(call.id, "您沒有權限管理操作員")
                return
                
            # 顯示當前操作員列表
            config = load_data(BOT_CONFIG_FILE)
            operators = config.get('operators', [])
            
            operators_text = "目前沒有操作員" if not operators else "\n".join([f"- {op}" for op in operators])
            
            msg_text = f"""👥 <b>操作員管理</b>

當前操作員列表：
{operators_text}

請輸入要添加或移除的操作員ID，格式如下：
添加: <code>+123456789</code>
移除: <code>-123456789</code>
"""
            msg = bot.send_message(call.message.chat.id, msg_text, parse_mode='HTML')
            
            # 設置用戶狀態為等待操作員管理輸入
            user_states[user_id] = {
                'state': 'waiting_operator_input',
                'prompt_msg_id': msg.message_id
            }
        
        # 其他按鈕處理可以根據需要添加
        else:
            # 處理未知的回調數據
            bot.answer_callback_query(call.id, "此功能尚未實現")
            
        # 確認回調處理完成
        if not call.data.startswith("back_to_menu"):
            try:
                bot.answer_callback_query(call.id)
            except:
                pass
            
    except Exception as e:
        error_msg = f"處理按鈕點擊時出錯: {str(e)}"
        if 'logger' in globals():
            logger.error(error_msg)
        try:
            bot.answer_callback_query(call.id, "處理請求時出錯，請稍後重試")
        except:
            pass

# 處理用戶文本輸入
@bot.message_handler(func=lambda message: message.from_user.id in user_states and message.reply_to_message is not None)
@error_handler
def handle_user_input(message):
    """處理用戶在各種狀態下的文本輸入"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    state = user_states.get(user_id, {}).get('state', '')
    
    # 確保回复的是正確的提示消息
    expected_msg_id = user_states.get(user_id, {}).get('prompt_msg_id')
    if message.reply_to_message.message_id != expected_msg_id:
        return
        
    if 'logger' in globals():
        logger.info(f"處理用戶 {message.from_user.username or user_id} 在狀態 {state} 的輸入: '{text}'")
    
    try:
        # 根據用戶當前狀態處理不同的輸入
        if state == 'waiting_tw_input':
            # 處理台幣輸入
            parts = text.strip().split()
            
            # 解析金額
            try:
                amount = float(parts[0].replace(',', ''))
            except ValueError:
                bot.reply_to(message, "❌ 金額格式不正確，請輸入有效的數字。")
                return
                
            # 解析日期
            if len(parts) > 1:
                date_str = parts[1]
                dt = parse_date(date_str)
            else:
                dt = datetime.now()
                
            date = dt.strftime('%Y-%m-%d')
            
            # 添加交易記錄
            add_transaction(user_id, date, "TW", amount)
            
            # 發送確認訊息
            bot.reply_to(message, f"✅ 已添加台幣入帳：NT${amount:,.0f} ({date})")
            
            # 生成並發送更新後的報表
            report = generate_report(user_id)
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            bot.send_message(chat_id, report, reply_markup=keyboard, parse_mode='HTML')
            
        elif state == 'waiting_cn_input':
            # 處理人民幣輸入
            parts = text.strip().split()
            
            # 解析金額
            try:
                amount = float(parts[0].replace(',', ''))
            except ValueError:
                bot.reply_to(message, "❌ 金額格式不正確，請輸入有效的數字。")
                return
                
            # 解析日期
            if len(parts) > 1:
                date_str = parts[1]
                dt = parse_date(date_str)
            else:
                dt = datetime.now()
                
            date = dt.strftime('%Y-%m-%d')
            
            # 添加交易記錄
            add_transaction(user_id, date, "CN", amount)
            
            # 發送確認訊息
            bot.reply_to(message, f"✅ 已添加人民幣入帳：CN¥{amount:,.0f} ({date})")
            
            # 生成並發送更新後的報表
            report = generate_report(user_id)
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            bot.send_message(chat_id, report, reply_markup=keyboard, parse_mode='HTML')
            
        elif state == 'waiting_rate_input':
            # 處理匯率輸入
            try:
                rate = float(text.strip())
                if rate <= 0:
                    bot.reply_to(message, "❌ 匯率必須大於零。")
                    return
            except ValueError:
                bot.reply_to(message, "❌ 匯率格式不正確，請輸入有效的數字。")
                return
                
            # 更新匯率
            set_rate(rate)
            
            # 發送確認訊息
            bot.reply_to(message, f"✅ 已更新台幣匯率為：{rate}")
            
            # 發送主選單
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            bot.send_message(chat_id, "匯率已更新。請選擇下一步操作：", reply_markup=keyboard)
            
        elif state == 'waiting_report_name':
            # 處理報表名稱輸入
            name = text.strip()
            if not name:
                bot.reply_to(message, "❌ 報表名稱不能為空。")
                return
                
            # 更新報表名稱
            set_report_name(user_id, name)
            
            # 發送確認訊息
            bot.reply_to(message, f"✅ 已更新報表名稱為：{name}")
            
            # 生成並發送更新後的報表
            report = generate_report(user_id)
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            bot.send_message(chat_id, report, reply_markup=keyboard, parse_mode='HTML')
            
        elif state == 'waiting_operator_input':
            # 處理操作員管理輸入
            input_text = text.strip()
            
            # 確認輸入格式
            if not (input_text.startswith('+') or input_text.startswith('-')):
                bot.reply_to(message, "❌ 輸入格式不正確，請使用 +ID 添加或 -ID 移除操作員。")
                return
                
            action = input_text[0]  # '+' 或 '-'
            op_id = input_text[1:].strip()
            
            # 驗證 ID
            try:
                op_id = int(op_id)
            except ValueError:
                bot.reply_to(message, "❌ ID 必須是數字。")
                return
                
            # 執行操作
            config = load_data(BOT_CONFIG_FILE)
            if 'operators' not in config:
                config['operators'] = []
                
            operators = config['operators']
            str_op_id = str(op_id)
            
            if action == '+':
                # 添加操作員
                if str_op_id not in [str(op) for op in operators]:
                    operators.append(op_id)
                    save_data(config, BOT_CONFIG_FILE)
                    bot.reply_to(message, f"✅ 已添加操作員：{op_id}")
                else:
                    bot.reply_to(message, f"ℹ️ 該 ID 已經是操作員。")
            else:
                # 移除操作員
                if str_op_id in [str(op) for op in operators]:
                    operators = [op for op in operators if str(op) != str_op_id]
                    config['operators'] = operators
                    save_data(config, BOT_CONFIG_FILE)
                    bot.reply_to(message, f"✅ 已移除操作員：{op_id}")
                else:
                    bot.reply_to(message, f"ℹ️ 該 ID 不是操作員。")
            
            # 更新操作員列表顯示
            operators = config.get('operators', [])
            operators_text = "目前沒有操作員" if not operators else "\n".join([f"- {op}" for op in operators])
            
            msg_text = f"""👥 <b>操作員管理</b>

當前操作員列表：
{operators_text}

請輸入要添加或移除的操作員ID，格式如下：
添加: <code>+123456789</code>
移除: <code>-123456789</code>
"""
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
            bot.send_message(chat_id, msg_text, reply_markup=keyboard, parse_mode='HTML')
        
    except Exception as e:
        error_msg = f"處理用戶輸入時出錯: {str(e)}"
        if 'logger' in globals():
            logger.error(error_msg)
        bot.reply_to(message, f"❌ 處理輸入時出錯: {str(e)}")
    finally:
        # 清除用戶狀態
        if user_id in user_states:
            del user_states[user_id]

# 添加 /report 命令處理
@bot.message_handler(commands=['report'])
@error_handler
def handle_report_command(message):
    """處理 /report 命令，顯示當月報表"""
    user_id = message.from_user.id
    report = generate_report(user_id)
    
    # 添加月份選擇按鈕
    now = datetime.now()
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    # 添加最近3個月的按鈕
    month_buttons = []
    for i in range(3):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        month_buttons.append(
            InlineKeyboardButton(
                f"{year}年{month}月",
                callback_data=f"report_month_{month}_{year}"
            )
        )
    
    keyboard.add(*month_buttons)
    keyboard.add(InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, report, reply_markup=keyboard, parse_mode='HTML')

# 簡單的健康檢查 Web 服務器
class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        status = 200
        response = {"status": "ok", "bot_running": True, "uptime": str(datetime.now() - BOT_START_TIME)}
        
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        if 'logger' in globals():
            logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

# 啟動 Web 服務器
def start_web_server(port=10000):
    """啟動簡單的健康檢查 Web 服務器"""
    try:
        server = socketserver.TCPServer(("0.0.0.0", port), HealthCheckHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        if 'logger' in globals():
            logger.info(f"健康檢查 Web 服務器已啟動在端口 {port}")
        else:
            print(f"健康檢查 Web 服務器已啟動在端口 {port}")
        return server
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"啟動 Web 服務器時出錯: {e}")
        else:
            print(f"啟動 Web 服務器時出錯: {e}")
        return None

# 運行機器人函數
def run_bot():
    """運行機器人的主函數"""
    try:
        # 初始化日誌
        global logger
        logger = setup_logging()
        logger.info("初始化機器人...")
        
        # 初始化數據文件
        init_files()
        
        # 確保機器人設定檔存在
        if not os.path.exists(BOT_CONFIG_FILE):
            with open(BOT_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "deposit_rate": 33.3,
                    "withdrawal_rate": 33.25,
                    "operators": [],
                    "transactions": [],
                    "processed_amount": 0.0
                }, f, ensure_ascii=False, indent=2)
            logger.info("創建了機器人設定檔")
        
        # 如果在 Render 環境中，啟動 Web 服務器
        if os.environ.get('RENDER') == 'true':
            port = int(os.environ.get('PORT', 10000))
            web_server = start_web_server(port)
            logger.info(f"在 Render 環境中運行，已啟動健康檢查 Web 服務器在端口 {port}")
            
        # 發送啟動通知
        try:
            send_startup_notification()
        except Exception as e:
            logger.error(f"發送啟動通知時出錯: {e}")
        
        # 啟動機器人
        logger.info(f"機器人啟動中，TOKEN: {BOT_TOKEN[:5]}..." if len(BOT_TOKEN) > 5 else "機器人啟動中，但未設置TOKEN")
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        logger.error(f"機器人啟動時出錯: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

# 直接運行檔案時的入口點
if __name__ == "__main__":
    run_bot() 