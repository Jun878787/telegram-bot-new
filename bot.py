import telebot
import logging
import os
import json
import re
import calendar
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sys
import subprocess
import threading
import time
import traceback
import signal
import psutil
import platform
from functools import wraps
import inspect

# 定義目標群組ID（請替換成你自己的群組ID）
TARGET_GROUP_ID = -1002229824712  # 替換成你提供的ID

# 定義管理員ID列表
ADMIN_IDS = [7842840472]  # 這裡添加管理員的用戶ID，例如 [123456789, 987654321]

# 檢查用戶是否為管理員或操作員
def is_admin(user_id, chat_id=None, check_operator=True):
    """檢查用戶是否為管理員或操作員"""
    # 如果用戶ID在管理員列表中
    if user_id in ADMIN_IDS:
        return True   
    # 如果提供了聊天ID，檢查用戶在該聊天中的狀態
    if chat_id:
        try:
            # 檢查是否為管理員
            chat_member = bot.get_chat_member(chat_id, user_id)
            if chat_member.status in ['creator', 'administrator']:
                return True
            
            # 如果需要檢查操作員身份
            if check_operator:
                # 加載設定
                settings = load_data(USER_SETTINGS_FILE)
                chat_id_str = str(chat_id)
                
                # 檢查用戶是否為操作員
                if (chat_id_str in settings and 
                    'operators' in settings[chat_id_str] and 
                    str(user_id) in settings[chat_id_str]['operators']):
                    return True
        except Exception as e:
            logger.error(f"檢查管理員狀態時出錯: {str(e)}")
    
    return False

# 在機器人啟動時發送通知到群組
def send_startup_notification():
    """向目標群組發送機器人啟動通知"""
    try:
        message = "🤖 機器人已啟動完成，可以開始使用！\n   ⌨️ 可輸入 /start 來重新整理出按鈕"
        bot.send_message(TARGET_GROUP_ID, message)
        logger.info(f"已發送啟動通知到群組 {TARGET_GROUP_ID}")
    except Exception as e:
        logger.error(f"發送啟動通知失敗: {str(e)}")

# 初始化機器人
bot = telebot.TeleBot('7498665144:AAGp_qX5YDVTu29K-pTLRTcikIo2OV2URGA')

# 檔案路徑
DATA_FILE = 'accounting_data.json'
USER_SETTINGS_FILE = 'user_settings.json'
EXCHANGE_RATES_FILE = 'exchange_rates.json'
PUBLIC_PRIVATE_FILE = 'funds.json'
OPERATOR_FILE = 'operators.json'
WELCOME_FILE = 'welcome.json'
WARNINGS_FILE = 'warnings.json'
LOG_FILE = 'bot.log'
# 特殊用戶名稱
SPECIAL_USER_NAME = 'M8P總表'

# 新增相關導入
import sys
import subprocess
import threading
import time
import traceback
import signal
import psutil
import platform

# 全局變量
RESTART_FLAG = False
BOT_START_TIME = datetime.now()
HEARTBEAT_INTERVAL = 60  # 心跳檢測間隔(秒)
MAX_ERROR_COUNT = 5  # 容許的最大連續錯誤數量
ERROR_RESET_TIME = 600  # 錯誤計數器重置時間(秒)
error_count = 0
last_error_time = None
heartbeat_thread = None

# 用户狀態字典，用於跟踪每個用户正在執行的操作
user_states = {}

# 設置日誌
def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = f'logs/bot_log_{current_date}.txt'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()]
    )
    return logging.getLogger('BotLogger')

logger = setup_logging()

# 初始化檔案
def init_files():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    if not os.path.exists(USER_SETTINGS_FILE):
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    if not os.path.exists(EXCHANGE_RATES_FILE):
        with open(EXCHANGE_RATES_FILE, 'w', encoding='utf-8') as f:
            json.dump({datetime.now().strftime('%Y-%m-%d'): 33.25}, f)
    if not os.path.exists(PUBLIC_PRIVATE_FILE):
        with open(PUBLIC_PRIVATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"public": 0, "private": 0}, f)
    if not os.path.exists(OPERATOR_FILE):
        with open(OPERATOR_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    if not os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    if not os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

# 資料操作函數
def load_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_data(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 使用者設定
def get_report_name(user_id):
    settings = load_data(USER_SETTINGS_FILE)
    return settings.get(str(user_id), {}).get('report_name', '總表')

def set_report_name(user_id, name):
    settings = load_data(USER_SETTINGS_FILE)
    if str(user_id) not in settings:
        settings[str(user_id)] = {}
    settings[str(user_id)]['report_name'] = name
    save_data(settings, USER_SETTINGS_FILE)

# 匯率操作
def get_rate(date=None):
    rates = load_data(EXCHANGE_RATES_FILE)
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    return rates.get(date, 33.25)

def set_rate(rate, date=None):
    rates = load_data(EXCHANGE_RATES_FILE)
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    rates[date] = float(rate)
    save_data(rates, EXCHANGE_RATES_FILE)

# 交易記錄操作
def add_transaction(user_id, date, type_currency, amount):
    data = load_data(DATA_FILE)
    if str(user_id) not in data:
        data[str(user_id)] = {}
    if date not in data[str(user_id)]:
        data[str(user_id)][date] = {"TW": 0, "CN": 0}
    
    currency = "TW" if type_currency.startswith("TW") else "CN"
    data[str(user_id)][date][currency] = amount
    save_data(data, DATA_FILE)

def delete_transaction(user_id, date, currency):
    data = load_data(DATA_FILE)
    if str(user_id) in data and date in data[str(user_id)]:
        data[str(user_id)][date][currency] = 0
        save_data(data, DATA_FILE)
        return True
    return False

# 公私桶資金操作
def update_fund(fund_type, amount):
    funds = load_data(PUBLIC_PRIVATE_FILE)
    funds[fund_type] += float(amount)
    save_data(funds, PUBLIC_PRIVATE_FILE)

# 日期解析
def parse_date(date_str):
    today = datetime.now()
    
    if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str):
        return date_str
    elif re.match(r'^\d{1,2}/\d{1,2}$', date_str):
        month, day = map(int, date_str.split('/'))
        return f"{today.year}-{month:02d}-{day:02d}"
    elif re.match(r'^\d{1,2}-\d{1,2}$', date_str):
        month, day = map(int, date_str.split('-'))
        return f"{today.year}-{month:02d}-{day:02d}"
    else:
        return today.strftime('%Y-%m-%d')

# 生成月報表
def generate_report(user_id, month=None, year=None):
    """生成指定月份的報表"""
    if month is None or year is None:
        now = datetime.now()
        month, year = now.month, now.year
    
    data = load_data(DATA_FILE)
    exchange_rates = load_data(EXCHANGE_RATES_FILE)
    funds = load_data(PUBLIC_PRIVATE_FILE)
    user_data = data.get(str(user_id), {})
    
    # 計算當月日期範圍
    _, last_day = calendar.monthrange(year, month)
    month_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
    
    # 計算總額及準備報表行
    tw_total, cn_total = 0, 0
    report_lines = []
    
    for date in month_dates:
        dt = datetime.strptime(date, '%Y-%m-%d')
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

# 清理舊數據（3個月前）
def clean_old_data():
    cutoff_date = datetime.now() - timedelta(days=90)
    
    # 清理會計資料
    data = load_data(DATA_FILE)
    for user_id in data:
        for date in list(data[user_id].keys()):
            try:
                if datetime.strptime(date, '%Y-%m-%d') < cutoff_date:
                    del data[user_id][date]
            except:
                pass
    save_data(data, DATA_FILE)
    
    # 清理匯率資料
    rates = load_data(EXCHANGE_RATES_FILE)
    for date in list(rates.keys()):
        try:
            if datetime.strptime(date, '%Y-%m-%d') < cutoff_date:
                del rates[date]
        except:
            pass
    save_data(rates, EXCHANGE_RATES_FILE)

# 創建改進後的鍵盤按鈕
def create_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        KeyboardButton('📊查看本月報表'),
        KeyboardButton('📚歷史報表')
    )
    keyboard.row(
        KeyboardButton('💰TW'),
        KeyboardButton('💰CN'),
        KeyboardButton('📋指令說明')
    )
    keyboard.row(
        KeyboardButton('💵公桶'),
        KeyboardButton('💵私人'),
        KeyboardButton('⚙️群管設定')
    )
    keyboard.row(
        KeyboardButton('💱設置匯率'),
        KeyboardButton('🔧設定')
    )
    return keyboard

# 歷史報表鍵盤
def create_history_keyboard():
    now = datetime.now()
    keyboard = InlineKeyboardMarkup()
    
    for i in range(6):
        month_date = now.replace(day=1) - timedelta(days=1)
        month_date = month_date.replace(day=1)
        month_date = month_date.replace(month=now.month - i if now.month > i else 12 - (i - now.month))
        month_date = month_date.replace(year=now.year if now.month > i else now.year - 1)
        
        month_str = month_date.strftime('%Y-%m')
        display = month_date.strftime('%Y年%m月')
        keyboard.add(InlineKeyboardButton(display, callback_data=f"history_{month_str}"))
    
    return keyboard

# 獲取進程信息
def get_process_info():
    pid = os.getpid()
    process = psutil.Process(pid)
    
    # 獲取進程信息
    memory_info = process.memory_info()
    cpu_percent = process.cpu_percent(interval=0.1)
    
    return {
        "pid": pid,
        "cpu_percent": cpu_percent,
        "memory_usage": f"{memory_info.rss / (1024 * 1024):.2f} MB",
        "uptime": str(datetime.now() - BOT_START_TIME).split('.')[0]  # 去除微秒
    }

# 重啟機器人
def restart_bot():
    """重新啟動機器人進程"""
    global RESTART_FLAG
    RESTART_FLAG = True
    
    logger.info("準備重啟機器人...")
    print("準備重啟機器人...")
    
    # 根據操作系統選擇重啟方法
    if platform.system() == "Windows":
        logger.info("Windows系統下重啟機器人...")
        print("Windows系統下重啟機器人...")
        # 使用subprocess在Windows中啟動新進程
        subprocess.Popen([sys.executable, __file__], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        logger.info("Unix系統下重啟機器人...")
        print("Unix系統下重啟機器人...")
        # 在Unix系統中使用exec直接替換當前進程
        os.execv(sys.executable, ['python'] + sys.argv)
    
    # 設置延遲退出以確保新進程已啟動
    logger.info("延遲3秒後退出當前進程...")
    print("延遲3秒後退出當前進程...")
    timer = threading.Timer(3.0, lambda: os.kill(os.getpid(), signal.SIGTERM))
    timer.daemon = True
    timer.start()

# 心跳檢測函數
def heartbeat_task():
    """定期檢查機器人狀態，並在必要時自動重啟"""
    last_check_time = datetime.now()
    
    while True:
        try:
            current_time = datetime.now()
            # 檢查是否有發送消息的能力
            # 這裡可以嘗試向一個預設的安全頻道發送測試消息，或者只是檢查Telegram API連接
            
            # 獲取進程信息用於日誌記錄
            process_info = get_process_info()
            logger.info(f"心跳檢測: PID={process_info['pid']}, "
                       f"CPU={process_info['cpu_percent']}%, "
                       f"內存={process_info['memory_usage']}, "
                       f"運行時間={process_info['uptime']}")
            
            # 如果長時間無活動，可以考慮發送一個空的API請求以保持連接
            if (current_time - last_check_time).total_seconds() > 300:  # 每5分鐘
                try:
                    bot.get_me()  # 嘗試獲取機器人信息，檢測連接是否正常
                    last_check_time = current_time
                except Exception as e:
                    logger.error(f"心跳檢測API請求失敗: {str(e)}")
                    # 如果連續多次失敗，可以考慮重啟
                    restart_bot()
                    break
            
            # 檢查記憶體使用，如果過高則重啟
            if psutil.virtual_memory().percent > 90:  # 系統記憶體使用>90%
                logger.warning("系統記憶體使用率過高，準備重啟機器人")
                restart_bot()
                break
                
            # 檢查自身記憶體使用，如果過高則重啟
            memory_value = float(process_info['memory_usage'].split()[0])  # 轉換為浮點數
            if memory_value > 500:  # 如果使用>500MB
                logger.warning("機器人記憶體使用率過高，準備重啟機器人")
                restart_bot()
                break
            
            # 睡眠一段時間
            time.sleep(HEARTBEAT_INTERVAL)
            
        except Exception as e:
            logger.error(f"心跳檢測出錯: {str(e)}")
            time.sleep(HEARTBEAT_INTERVAL)  # 出錯也要繼續循環

# 啟動心跳檢測
def start_heartbeat():
    global heartbeat_thread
    heartbeat_thread = threading.Thread(target=heartbeat_task, daemon=True)
    heartbeat_thread.start()
    logger.info("心跳檢測線程已啟動")

# 錯誤處理裝飾器
def error_handler(func):
    """裝飾器：用於處理函數執行期間的錯誤，記錄日誌並向管理員發送通知"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global error_count, last_error_time
        try:
            # 嘗試執行原始函數
            return func(*args, **kwargs)
        except Exception as e:
            # 捕獲錯誤並處理
            traceback_text = traceback.format_exc()
            
            # 獲取當前時間
            current_time = datetime.now()
            
            # 如果上次錯誤時間超過重置時間，重置錯誤計數
            if last_error_time and (current_time - last_error_time).total_seconds() > ERROR_RESET_TIME:
                error_count = 0
            
            # 更新上次錯誤時間
            last_error_time = current_time
            
            # 增加錯誤計數
            error_count += 1
            
            # 獲取錯誤發生時的堆棧信息
            frame = inspect.currentframe().f_back
            func_name = func.__name__
            file_name = inspect.getfile(frame)
            line_number = frame.f_lineno
            code_context = inspect.getframeinfo(frame).code_context
            
            # 獲取錯誤發生處的代碼行
            code_line = code_context[0].strip() if code_context else "Unknown code"
            
            # 記錄錯誤信息到日誌
            error_log = f"錯誤發生在 {file_name}:{line_number} - 函數 {func_name}() - 代碼: {code_line}\n{traceback_text}"
            logger.error(error_log)
            
            # 分析錯誤信息，獲取可讀的錯誤描述
            error_description = analyze_error(e, traceback_text)
            
            # 嘗試發送錯誤信息到管理員
            try:
                # 如果args[0]是telebot.types.Message對象，則可能需要發送回覆
                if args and hasattr(args[0], 'chat') and hasattr(args[0], 'from_user'):
                    message = args[0]
                    
                    # 回覆用戶，告知有錯誤發生
                    user_error_msg = f"處理請求時發生錯誤: {str(e)}，錯誤已記錄。"
                    bot.reply_to(message, user_error_msg)
                    
                    # 檢查是否需要發送完整錯誤信息到管理員
                    admin_ids = get_admin_ids()
                    if message.from_user.id not in admin_ids:
                        # 發送錯誤通知到管理員
                        admin_error_msg = (
                            f"⚠️ 機器人錯誤通知 ⚠️\n"
                            f"錯誤時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"錯誤來源: 用戶 {message.from_user.id} ({message.from_user.username or 'Unknown'})\n"
                            f"錯誤消息: {message.text if hasattr(message, 'text') else 'N/A'}\n"
                            f"錯誤類型: {type(e).__name__}\n"
                            f"錯誤描述: {error_description}\n"
                            f"錯誤位置: {file_name}:{line_number} in {func_name}()\n"
                            f"錯誤代碼: {code_line}"
                        )
                        
                        # 向所有管理員發送錯誤通知
                        for admin_id in admin_ids:
                            try:
                                bot.send_message(admin_id, admin_error_msg)
                            except Exception:
                                pass  # 忽略發送到管理員的錯誤
            except Exception as notify_error:
                logger.error(f"嘗試發送錯誤通知時出錯: {str(notify_error)}")
            
            # 檢查是否需要重啟機器人（錯誤計數超過閾值）
            if error_count >= MAX_ERROR_COUNT:
                logger.critical(f"錯誤計數達到{error_count}，機器人將自動重啟")
                
                try:
                    # 發送重啟通知
                    bot.send_message(TARGET_GROUP_ID, "⚠️ 機器人遇到多次錯誤，正在自動重啟...")
                except Exception:
                    pass
                
                # 重啟機器人
                restart_bot()
            
            # 重新拋出異常，或返回默認值
            # raise e  # 取消註釋以重新拋出異常
    
    return wrapper

# 特殊用戶資金設定
def set_special_user_funds(fund_type, amount):
    """設置特殊用戶的公桶或私人資金"""
    settings = load_data(USER_SETTINGS_FILE)
    if SPECIAL_USER_NAME not in settings:
        settings[SPECIAL_USER_NAME] = {}
    
    settings[SPECIAL_USER_NAME][fund_type] = float(amount)
    save_data(settings, USER_SETTINGS_FILE)

# 獲取特殊用戶資金
def get_special_user_funds(fund_type):
    """獲取特殊用戶的公桶或私人資金"""
    settings = load_data(USER_SETTINGS_FILE)
    return settings.get(SPECIAL_USER_NAME, {}).get(fund_type, 0)

def generate_combined_report(month=None, year=None):
    """生成所有用戶資料總和的綜合報表"""
    if month is None or year is None:
        now = datetime.now()
        month, year = now.month, now.year
    
    data = load_data(DATA_FILE)
    exchange_rates = load_data(EXCHANGE_RATES_FILE)
    funds = load_data(PUBLIC_PRIVATE_FILE)
    
    # 計算當月日期範圍
    _, last_day = calendar.monthrange(year, month)
    month_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
    
    # 計算總額及準備報表行
    tw_total, cn_total = 0, 0
    combined_data = {}
    
    # 首先彙整所有用戶數據
    for user_id, user_data in data.items():
        for date, day_data in user_data.items():
            if date.startswith(f"{year}-{month:02d}"):
                if date not in combined_data:
                    combined_data[date] = {"TW": 0, "CN": 0}
                
                combined_data[date]["TW"] += day_data.get("TW", 0)
                combined_data[date]["CN"] += day_data.get("CN", 0)
    
    report_lines = []
    
    for date in month_dates:
        dt = datetime.strptime(date, '%Y-%m-%d')
        day_str = dt.strftime('%m/%d')
        weekday = dt.weekday()
        weekday_str = ('一', '二', '三', '四', '五', '六', '日')[weekday]
        
        day_data = combined_data.get(date, {"TW": 0, "CN": 0})
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
    
    # 獲取公桶和私人資金設定
    settings = load_data(USER_SETTINGS_FILE)
    special_settings = settings.get(SPECIAL_USER_NAME, {})
    
    # 使用特殊用戶的公桶和私人資金設定，如果沒有則使用默認值
    public_funds = special_settings.get('public_funds', funds.get('public', 0))
    private_funds = special_settings.get('private_funds', funds.get('private', 0))
    
    public_funds_display = f"{public_funds:.0f}"
    private_funds_display = f"{private_funds:.0f}"
    
    # 格式化數字
    tw_total_display = f"{tw_total:,.0f}"
    cn_total_display = f"{cn_total:,.0f}"
    
    # 報表頭部更新 - 使用更清晰的格式
    header = [
        f"<b>【總合報表】</b>",
        f"<b>◉ 台幣總業績</b>",
        f"<code>NT${tw_total_display}</code>",
        f"<b>◉ 人民幣總業績</b>",
        f"<code>CN¥{cn_total_display}</code>",
        f"<b>◉ 資金狀態</b>",
        f"公桶: <code>USDT${public_funds_display}</code>",
        f"私人: <code>USDT${private_funds_display}</code>",
        "－－－－－－－－－－",
        f"<b>{year}年{month}月收支明細</b>"
    ]
    
    return "\n".join(header + report_lines)

# # 生成特殊用戶綜合報表 - 此函數已移至文件前面，這裡只是保留一個轉發
def generate_combined_report_old(month=None, year=None):
    """此函數已移至文件前面，請使用前面的版本"""
    # 轉發到前面定義的函數
    from inspect import currentframe, getframeinfo
    logger.warning(f"在 {getframeinfo(currentframe()).filename}:{getframeinfo(currentframe()).lineno} 調用了舊版的 generate_combined_report 函數")
    return generate_combined_report(month, year)

# 【最高優先級】處理總表相關指令
@bot.message_handler(func=lambda message: message.text and message.text.strip() in ['總表', '總表資金'] or 
                                         (message.text and re.match(r'^總表\s+\d{4}-\d{1,2}$', message.text.strip())), 
                     content_types=['text'])
@error_handler
def handle_total_report_commands_highest_priority(message):
    """最高優先級處理器 - 總表相關指令"""
    text = message.text.strip()
    logger.info(f"【最高優先級】捕獲到總表相關指令: '{text}'，來自用戶 {message.from_user.username or message.from_user.id}")
    
    try:
        if text == '總表':
            # 處理總表指令
            report = generate_combined_report()
            bot.reply_to(message, report, parse_mode='HTML')
            logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了總表")
            
        elif text == '總表資金':
            # 處理總表資金指令
            public_funds = get_special_user_funds('public_funds')
            private_funds = get_special_user_funds('private_funds')
            
            funds_info = (
                f"<b>【M8P總表資金狀態】</b>\n"
                f"公桶: <code>USDT${public_funds:.0f}</code>\n"
                f"私人: <code>USDT${private_funds:.0f}</code>"
            )
            
            bot.reply_to(message, funds_info, parse_mode='HTML')
            logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了總表資金狀態")
            
        elif re.match(r'^總表\s+\d{4}-\d{1,2}$', text):
            # 處理歷史總表指令
            match = re.match(r'^總表\s+(\d{4})-(\d{1,2})$', text)
            year = int(match.group(1))
            month = int(match.group(2))
            
            report = generate_combined_report(month, year)
            bot.reply_to(message, report, parse_mode='HTML')
            logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了 {year}-{month} 總表")
    except Exception as e:
        bot.reply_to(message, f"❌ 處理總表指令時發生錯誤：{str(e)}")
        logger.error(f"處理總表指令錯誤：{str(e)}")
        logger.error(traceback.format_exc())  # 添加詳細的錯誤追蹤

# 錯誤分析函數
def analyze_error(error, traceback_text):
    """分析錯誤並提供可能的解決方案"""
    error_type = type(error).__name__
    error_msg = str(error).lower()
    
    # 網絡連接錯誤
    if error_type in ['ConnectionError', 'ReadTimeout', 'ConnectTimeout', 'HTTPError']:
        return "網絡連接問題。請檢查網絡連接或Telegram API伺服器狀態。"
    
    # API錯誤
    elif error_type == 'ApiTelegramException' or 'telegram' in error_msg:
        if 'blocked' in error_msg or 'kicked' in error_msg:
            return "機器人被用戶封鎖或踢出群組。"
        elif 'flood' in error_msg or 'too many requests' in error_msg:
            return "發送消息過於頻繁，觸發了Telegram限流機制。"
        elif 'not enough rights' in error_msg or 'permission' in error_msg:
            return "機器人缺少執行此操作的權限。"
        elif 'chat not found' in error_msg:
            return "找不到指定的聊天。用戶可能已刪除聊天或離開群組。"
        else:
            return f"Telegram API錯誤: {error_msg}"
    
    # JSON解析錯誤
    elif error_type in ['JSONDecodeError', 'ValueError'] and ('json' in error_msg or 'parsing' in error_msg):
        return "JSON解析錯誤，可能是數據文件格式錯誤。"
    
    # 文件IO錯誤
    elif error_type in ['FileNotFoundError', 'PermissionError', 'IOError']:
        return "文件操作錯誤，請檢查文件權限或磁盤空間。"
    
    # 類型錯誤
    elif error_type in ['TypeError', 'AttributeError']:
        return "程式邏輯錯誤，可能是資料結構不符合預期。"
    
    # 索引錯誤
    elif error_type in ['IndexError', 'KeyError']:
        return "訪問不存在的數據，可能是資料結構變化或資料不完整。"
    
    # 正則表達式錯誤
    elif error_type == 'RegexError' or 're' in error_msg:
        return "正則表達式匹配錯誤。"
    
    # 其他未知錯誤
    else:
        return f"未知錯誤類型: {error_type}。查看日誌獲取詳細信息。"

# 獲取所有管理員ID
def get_admin_ids():
    """獲取所有在配置裡記錄的管理員ID"""
    try:
        # 這裡應該從配置文件或數據庫中獲取管理員ID
        # 簡化起見，這裡使用一個硬編碼的列表，實際應從設置讀取
        admin_settings = load_data(USER_SETTINGS_FILE)
        admin_ids = []
        
        for user_id, settings in admin_settings.items():
            if settings.get('is_admin', False):
                admin_ids.append(int(user_id))
        
        # 如果沒有設置管理員，返回一個預設值
        if not admin_ids:
            # 使用創建者ID作為管理員（實際應從設置獲取）
            # 這個ID可以在初始設置過程中由創建者設定
            creator_id = admin_settings.get('creator_id', None)
            if creator_id:
                admin_ids.append(int(creator_id))
        
        return admin_ids
    except Exception as e:
        logger.error(f"獲取管理員ID失敗: {str(e)}")
        return []  # 返回空列表

# 處理重啟命令 - 確保這個處理器比其他處理器先註冊，提高優先級
@bot.message_handler(func=lambda message: message.text.strip() == '重啟', content_types=['text'])
@error_handler
def handle_restart_text_priority(message):
    """處理純文字「重啟」命令，功能與 /restart 相同，高優先級版本"""
    logger.info(f"收到重啟命令(高優先級處理)，發送者: {message.from_user.id}")
    print(f"收到重啟命令(高優先級處理)，發送者: {message.from_user.id}")
    
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此命令僅限管理員使用")
        return
    
    # 發送重啟提示
    restart_msg = bot.reply_to(message, "🔄 機器人即將重新啟動，請稍候...")
    
    # 發送重啟提示到目標群組（如果不是在目標群組中）
    if message.chat.id != TARGET_GROUP_ID:
        try:
            bot.send_message(TARGET_GROUP_ID, "🔄 機器人正在重新啟動，請稍候...")
        except Exception as e:
            logger.error(f"無法發送重啟通知到群組: {str(e)}")
    
    # 延遲一下確保消息發送成功
    time.sleep(2)
    
    # 記錄重啟事件
    logger.info(f"管理員 {message.from_user.id} 觸發機器人重啟")
    
    # 設置重啟標記
    with open("restart_flag.txt", "w") as f:
        f.write(str(datetime.now()))
    
    # 重啟機器人
    restart_bot()

# 獲取機器人狀態
@bot.message_handler(func=lambda message: message.text in ['狀態', '機器人狀態'])
@error_handler
def handle_status(message):
    """返回機器人當前運行狀態"""
    # 檢查是否為管理員（可選，也可以向所有用戶開放）
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此命令僅限管理員使用")
        return
    
    # 獲取進程信息
    process_info = get_process_info()
    
    # 獲取機器人版本（如果有設定）
    version = "1.0.0"  # 硬編碼的版本號，實際應從某處獲取
    
    # 格式化運行時間
    uptime = process_info['uptime']
    
    # 構建狀態消息
    status_msg = (
        f"🤖 機器人狀態報告\n\n"
        f"✅ 機器人運行中\n"
        f"📊 版本: {version}\n"
        f"⏱ 運行時間: {uptime}\n"
        f"💻 CPU使用率: {process_info['cpu_percent']}%\n"
        f"💾 記憶體使用: {process_info['memory_usage']}\n"
        f"🔢 PID: {process_info['pid']}\n"
        f"📅 啟動時間: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    bot.reply_to(message, status_msg)

# 命令處理
@bot.message_handler(commands=['start'])
@error_handler
def send_welcome(message):
    """處理/start命令，顯示歡迎訊息和主選單"""
    init_files()
    bot.reply_to(message, "歡迎使用記帳機器人！", reply_markup=create_keyboard())
    logger.info(f"使用者 {message.from_user.username or message.from_user.id} 啟動了機器人")

# 新的按鈕處理函數
@bot.message_handler(func=lambda message: message.text in ['💰TW', '💰CN', '💵公桶', '💵私人'], content_types=['text'])
@error_handler
def handle_button_click_priority(message):
    """處理按鈕點擊，優先級版本"""
    # 原有的處理邏輯保持不變
    button_text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # 設置用户狀態，記錄當前操作類型
    operation_type = button_text.replace('💰', '').replace('💵', '')
    user_states[user_id] = {'operation': operation_type, 'chat_id': chat_id}
    
    # 根據按鈕類型提供不同的說明和提示
    if 'TW' in button_text:
        prompt = (
            "📝 <b>台幣記帳</b>\n\n"
            "請<b>回覆此訊息</b>並輸入金額：\n\n"
            "<b>今日收入格式</b>：+金額\n"
            "例如：<code>+1000</code> 或 <code>+1234.56</code>\n\n"
            "<b>今日支出格式</b>：-金額\n"
            "例如：<code>-1000</code> 或 <code>-1234.56</code>\n\n"
            "<b>指定日期格式</b>：日期 [+/-]金額\n"
            "例如：<code>5/01 +350000</code> 或 <code>5-01 -1000</code>\n\n"
            "系統會根據符號判斷這筆記錄為收入或支出。\n"
            "日期格式支援：MM/DD、MM-DD、YYYY-MM-DD"
        )
    elif 'CN' in button_text:
        prompt = (
            "📝 <b>人民幣記帳</b>\n\n"
            "請<b>回覆此訊息</b>並輸入金額：\n\n"
            "<b>收入格式</b>：+金額\n"
            "例如：<code>+1000</code> 或 <code>+1234.56</code>\n\n"
            "<b>支出格式</b>：-金額\n"
            "例如：<code>-1000</code> 或 <code>-1234.56</code>\n\n"
            "系統會根據符號判斷這筆記錄為收入或支出。"
        )
    elif '公桶' in button_text:
        prompt = (
            "📝 <b>公桶資金記帳</b>\n\n"
            "請<b>回覆此訊息</b>並輸入金額：\n\n"
            "<b>增加格式</b>：+金額\n"
            "例如：<code>+100</code> 或 <code>+123.45</code>\n\n"
            "<b>減少格式</b>：-金額\n"
            "例如：<code>-100</code> 或 <code>-123.45</code>\n\n"
            "系統會根據符號判斷是增加或減少公桶資金。"
        )
    elif '私人' in button_text:
        prompt = (
            "📝 <b>私人資金記帳</b>\n\n"
            "請<b>回覆此訊息</b>並輸入金額：\n\n"
            "<b>增加格式</b>：+金額\n"
            "例如：<code>+100</code> 或 <code>+123.45</code>\n\n"
            "<b>減少格式</b>：-金額\n"
            "例如：<code>-100</code> 或 <code>-123.45</code>\n\n"
            "系統會根據符號判斷是增加或減少私人資金。"
        )
    
    # 發送提示訊息，使用HTML格式增強可讀性
    # 儲存此訊息ID以便後續檢查是否為對此訊息的回覆
    sent_msg = bot.send_message(chat_id, prompt, parse_mode='HTML')
    user_states[user_id]['prompt_msg_id'] = sent_msg.message_id

# 處理回覆中的金額輸入
@bot.message_handler(func=lambda message: message.reply_to_message is not None and 
                                          message.from_user.id in user_states and 
                                          user_states[message.from_user.id].get('prompt_msg_id') == message.reply_to_message.message_id and
                                          (re.match(r'^[+\-]\d+(\.\d+)?$', message.text) or 
                                           re.match(r'^([0-9/\-\.]+)\s+[+\-]\d+(\.\d+)?$', message.text)))
@error_handler
def handle_reply_amount_input(message):
    """處理用戶在回覆中輸入的金額"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # 檢查用戶是否處於輸入金額的狀態
    if user_id not in user_states:
        return
    
    # 獲取操作類型
    operation = user_states[user_id].get('operation')
    
    # 檢查是否為日期加金額格式
    date_amount_match = re.match(r'^([0-9/\-\.]+)\s+([+\-])(\d+(\.\d+)?)$', message.text)
    
    if date_amount_match and operation in ['TW', 'CN']:
        # 處理日期 +/-金額 格式
        date_str = date_amount_match.group(1)
        is_positive = date_amount_match.group(2) == '+'
        amount = float(date_amount_match.group(3))
        
        # 如果是負數，使金額為負
        if not is_positive:
            amount = -amount
        
        # 轉換日期格式
        date = parse_date(date_str)
        date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
        
        # 根據操作類型記錄交易
        try:
            if operation == 'TW':
                add_transaction(user_id, date, 'TW', amount)
                if amount > 0:
                    response = f"✅ 已記錄 {date_display} 的台幣收入：NT${amount:,.0f}"
                else:
                    response = f"✅ 已記錄 {date_display} 的台幣支出：NT${-amount:,.0f}"
            elif operation == 'CN':
                add_transaction(user_id, date, 'CN', amount)
                if amount > 0:
                    response = f"✅ 已記錄 {date_display} 的人民幣收入：¥{amount:,.0f}"
                else:
                    response = f"✅ 已記錄 {date_display} 的人民幣支出：¥{-amount:,.0f}"
            
            # 發送回覆
            bot.reply_to(message, response)
            
            # 操作完成後，清除用戶狀態
            del user_states[user_id]
            
            # 記錄操作日誌
            logger.info(f"用戶 {message.from_user.username or user_id} 執行 {operation} 操作，日期：{date_display}，金額：{amount}")
            
            return
        except Exception as e:
            bot.reply_to(message, f"❌ 處理日期與金額時出錯：{str(e)}")
            logger.error(f"處理日期與金額輸入出錯: {str(e)}")
            # 出錯時也清除用戶狀態
            del user_states[user_id]
            return
    
    # 處理純金額格式（原有功能）
    try:
        # 判斷是收入還是支出
        is_positive = message.text.startswith('+')
        # 提取純數字金額
        amount = float(message.text[1:])  # 去掉正負號
        # 如果是負數，使金額為負
        if not is_positive:
            amount = -amount
        
        # 根據操作類型處理金額
        date = datetime.now().strftime('%Y-%m-%d')
        
        if operation == 'TW':
            add_transaction(user_id, date, 'TW', amount)
            if amount > 0:
                response = f"✅ 已記錄今日台幣收入：NT${amount:,.0f}"
            else:
                response = f"✅ 已記錄今日台幣支出：NT${-amount:,.0f}"
        elif operation == 'CN':
            add_transaction(user_id, date, 'CN', amount)
            if amount > 0:
                response = f"✅ 已記錄今日人民幣收入：¥{amount:,.0f}"
            else:
                response = f"✅ 已記錄今日人民幣支出：¥{-amount:,.0f}"
        elif operation == '公桶':
            update_fund("public", amount)
            if amount > 0:
                response = f"✅ 已添加公桶資金：USDT${amount:.2f}"
            else:
                response = f"✅ 已從公桶資金中扣除：USDT${-amount:.2f}"
        elif operation == '私人':
            update_fund("private", amount)
            if amount > 0:
                response = f"✅ 已添加私人資金：USDT${amount:.2f}"
            else:
                response = f"✅ 已從私人資金中扣除：USDT${-amount:.2f}"
        else:
            response = "❌ 無效的操作類型"
            
        # 發送回覆
        bot.reply_to(message, response)
        
        # 操作完成後，清除用戶狀態
        del user_states[user_id]
        
        # 記錄操作日誌
        logger.info(f"用戶 {message.from_user.username or user_id} 執行 {operation} 操作，金額：{amount}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ 處理金額時出錯：{str(e)}")
        logger.error(f"處理金額輸入出錯: {str(e)}")
        # 出錯時也清除用戶狀態
        del user_states[user_id]

# 提示未回覆訊息的錯誤
@bot.message_handler(func=lambda message: message.from_user.id in user_states and 
                                          (re.match(r'^[+\-]\d+(\.\d+)?$', message.text) or 
                                           re.match(r'^([0-9/\-\.]+)\s+[+\-]\d+(\.\d+)?$', message.text)) and
                                          (message.reply_to_message is None or 
                                           user_states[message.from_user.id].get('prompt_msg_id') != message.reply_to_message.message_id))
@error_handler
def handle_non_reply_amount(message):
    """提醒用戶需要回覆訊息輸入金額"""
    bot.reply_to(message, "❌ 請<b>回覆</b>之前的提示訊息輸入金額，而不是直接發送。", parse_mode='HTML')

# 設置匯率處理
@bot.message_handler(regexp=r'^設置今日匯率(\d+(\.\d+)?)$')
@error_handler
def handle_set_today_rate(message):
    # 檢查是否為管理員或操作員
    if not is_admin(message.from_user.id, message.chat.id, check_operator=True):
        bot.reply_to(message, "❌ 此功能僅限管理員或操作員使用")
        return
        
    match = re.match(r'^設置今日匯率(\d+(\.\d+)?)$', message.text)
    rate = float(match.group(1))
    
    set_rate(rate)
    
    bot.reply_to(message, f"✅ 已設置今日匯率為：{rate}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 設置今日匯率為 {rate}")

@bot.message_handler(regexp=r'^設置"([0-9/\-]+)"匯率(\d+(\.\d+)?)$')
@error_handler
def handle_set_date_rate(message):
    # 檢查是否為管理員或操作員
    if not is_admin(message.from_user.id, message.chat.id, check_operator=True):
        bot.reply_to(message, "❌ 此功能僅限管理員或操作員使用")
        return
        
    match = re.match(r'^設置"([0-9/\-]+)"匯率(\d+(\.\d+)?)$', message.text)
    date_str = match.group(1)
    rate = float(match.group(2))
    
    date = parse_date(date_str)
    
    set_rate(rate, date)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已設置 {date_display} 匯率為：{rate}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 設置 {date_display} 匯率為 {rate}")

# 刪除交易處理
@bot.message_handler(regexp=r'^刪除"([0-9/\-]+)"NTD金額$')
@error_handler
def handle_delete_ntd(message):
    match = re.match(r'^刪除"([0-9/\-]+)"NTD金額$', message.text)
    date_str = match.group(1)
    
    date = parse_date(date_str)
    
    if delete_transaction(message.from_user.id, date, "TW"):
        date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
        bot.reply_to(message, f"✅ 已刪除 {date_display} 的臺幣金額")
    else:
        bot.reply_to(message, "❌ 找不到該日期的交易記錄")

@bot.message_handler(regexp=r'^刪除"([0-9/\-]+)"CNY金額$')
@error_handler
def handle_delete_cny(message):
    match = re.match(r'^刪除"([0-9/\-]+)"CNY金額$', message.text)
    date_str = match.group(1)
    
    date = parse_date(date_str)
    
    if delete_transaction(message.from_user.id, date, "CN"):
        date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
        bot.reply_to(message, f"✅ 已刪除 {date_display} 的人民幣金額")
    else:
        bot.reply_to(message, "❌ 找不到該日期的交易記錄")

# 設定報表名稱
@bot.message_handler(regexp=r'^報表使用者設定\s+(.+)$')
@error_handler
def handle_set_report_name(message):
    match = re.match(r'^報表使用者設定\s+(.+)$', message.text)
    report_name = match.group(1)
    
    set_report_name(message.from_user.id, report_name)
    
    bot.reply_to(message, f"✅ 已設定報表名稱為：【{report_name}】")

# 查看本月報表
@bot.message_handler(func=lambda message: message.text == '📊查看本月報表')
@error_handler
def handle_show_report(message):
    try:
        report = generate_report(message.from_user.id)
        bot.reply_to(message, report, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ 生成報表時發生錯誤：{str(e)}")

# 查看歷史報表
@bot.message_handler(func=lambda message: message.text == '📚歷史報表')
@error_handler
def handle_history_reports(message):
    try:
        keyboard = create_history_keyboard()
        bot.reply_to(message, "請選擇要查看的月份：", reply_markup=keyboard)
    except Exception as e:
        bot.reply_to(message, f"❌ 顯示歷史報表選單時發生錯誤：{str(e)}")

# 處理回調查詢
@bot.callback_query_handler(func=lambda call: call.data.startswith('history_'))
@error_handler
def handle_history_callback(call):
    try:
        month_year = call.data.replace('history_', '')
        year, month = map(int, month_year.split('-'))
        report = generate_report(call.from_user.id, month, year)
        bot.send_message(call.message.chat.id, report, parse_mode='HTML')
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ 錯誤：{str(e)}")
        logger.error(f"處理歷史報表回調出錯：{str(e)}")

# 完成@使用者功能
@bot.message_handler(regexp=r'^@(\w+)\s+([0-9/\-]+)\s+TW\+(\d+(\.\d+)?)$')
@error_handler
def handle_user_date_tw_add(message):
    match = re.match(r'^@(\w+)\s+([0-9/\-]+)\s+TW\+(\d+(\.\d+)?)$', message.text)
    username = match.group(1)
    date_str = match.group(2)
    amount = float(match.group(3))
    
    date = parse_date(date_str)
    
    # 查找使用者ID
    target_user_id = None
    try:
        chat_members = bot.get_chat_administrators(message.chat.id)
        for member in chat_members:
            if member.user.username == username:
                target_user_id = member.user.id
                break
    except Exception as e:
        logger.error(f"獲取群組成員失敗：{str(e)}")
    
    if target_user_id is None:
        bot.reply_to(message, f"❌ 找不到使用者 @{username}")
        return
    
    add_transaction(target_user_id, date, 'TW', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已為 @{username} 記錄 {date_display} 的臺幣收入：NT${amount:,.0f}")

@bot.message_handler(regexp=r'^@(\w+)\s+([0-9/\-]+)\s+TW-(\d+(\.\d+)?)$')
@error_handler
def handle_user_date_tw_subtract(message):
    match = re.match(r'^@(\w+)\s+([0-9/\-]+)\s+TW-(\d+(\.\d+)?)$', message.text)
    username = match.group(1)
    date_str = match.group(2)
    amount = -float(match.group(3))
    
    date = parse_date(date_str)
    
    # 查找使用者ID
    target_user_id = None
    try:
        chat_members = bot.get_chat_administrators(message.chat.id)
        for member in chat_members:
            if member.user.username == username:
                target_user_id = member.user.id
                break
    except Exception as e:
        logger.error(f"獲取群組成員失敗：{str(e)}")
    
    if target_user_id is None:
        bot.reply_to(message, f"❌ 找不到使用者 @{username}")
        return
    
    add_transaction(target_user_id, date, 'TW', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已為 @{username} 記錄 {date_display} 的臺幣支出：NT${-amount:,.0f}")

@bot.message_handler(regexp=r'^@(\w+)\s+([0-9/\-]+)\s+CN\+(\d+(\.\d+)?)$')
@error_handler
def handle_user_date_cn_add(message):
    match = re.match(r'^@(\w+)\s+([0-9/\-]+)\s+CN\+(\d+(\.\d+)?)$', message.text)
    username = match.group(1)
    date_str = match.group(2)
    amount = float(match.group(3))
    
    date = parse_date(date_str)
    
    # 查找使用者ID
    target_user_id = None
    try:
        chat_members = bot.get_chat_administrators(message.chat.id)
        for member in chat_members:
            if member.user.username == username:
                target_user_id = member.user.id
                break
    except Exception as e:
        logger.error(f"獲取群組成員失敗：{str(e)}")
    
    if target_user_id is None:
        bot.reply_to(message, f"❌ 找不到使用者 @{username}")
        return
    
    add_transaction(target_user_id, date, 'CN', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已為 @{username} 記錄 {date_display} 的人民幣收入：¥{amount:,.0f}")

@bot.message_handler(regexp=r'^@(\w+)\s+([0-9/\-]+)\s+CN-(\d+(\.\d+)?)$')
@error_handler
def handle_user_date_cn_subtract(message):
    match = re.match(r'^@(\w+)\s+([0-9/\-]+)\s+CN-(\d+(\.\d+)?)$', message.text)
    username = match.group(1)
    date_str = match.group(2)
    amount = -float(match.group(3))
    
    date = parse_date(date_str)
    
    # 查找使用者ID
    target_user_id = None
    try:
        chat_members = bot.get_chat_administrators(message.chat.id)
        for member in chat_members:
            if member.user.username == username:
                target_user_id = member.user.id
                break
    except Exception as e:
        logger.error(f"獲取群組成員失敗：{str(e)}")
    
    if target_user_id is None:
        bot.reply_to(message, f"❌ 找不到使用者 @{username}")
        return
    
    add_transaction(target_user_id, date, 'CN', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已為 @{username} 記錄 {date_display} 的人民幣支出：¥{-amount:,.0f}")

# 設置匯率按鈕處理
@bot.message_handler(func=lambda message: message.text == '💱設置匯率')
@error_handler
def handle_rate_setting(message):
    try:
        current_rate = get_rate()
        bot.reply_to(message, 
            f"🔹 當前匯率：{current_rate}\n\n"
            f"修改匯率請使用以下格式：\n"
            f"- 設置今日匯率33.25\n"
            f"- 設置\"MM/DD\"匯率33.44"
        )
    except Exception as e:
        bot.reply_to(message, f"❌ 錯誤：{str(e)}")

# 設定按鈕處理
@bot.message_handler(func=lambda message: message.text == '🔧設定')
@error_handler
def handle_settings(message):
    try:
        settings_text = (
            "⚙️ 設定選項：\n\n"
            "🔹 報表使用者設定 [名稱]\n"
            "    例如：報表使用者設定 北區業績\n\n"
            "🔸 目前報表名稱：" + get_report_name(message.from_user.id)
        )
        bot.reply_to(message, settings_text)
    except Exception as e:
        bot.reply_to(message, f"❌ 錯誤：{str(e)}")

# 設定定期清理任務
def schedule_cleaning():
    import threading
    import time
    
    def cleaning_task():
        while True:
            try:
                logger.info("開始執行定期清理任務...")
                clean_old_data()
                logger.info("定期清理任務完成")
                # 每天執行一次
                time.sleep(86400)  # 24小時 = 86400秒
            except Exception as e:
                logger.error(f"定期清理任務出錯：{str(e)}")
                time.sleep(3600)  # 出錯后等待1小時再試
    
    # 啟動清理線程
    cleaning_thread = threading.Thread(target=cleaning_task, daemon=True)
    cleaning_thread.start()
    logger.info("定期清理線程已啟動")

# 處理查詢命令
@bot.message_handler(func=lambda message: message.text.lower() == 'help' or message.text == '幫助')
@error_handler
def handle_help(message):
    help_text = (
        "📋 記帳機器人使用說明\n\n"
        "➖➖➖ 基本命令 ➖➖➖\n"
        "TW+金額 - 記錄臺幣收入\n"
        "TW-金額 - 記錄臺幣支出\n"
        "CN+金額 - 記錄人民幣收入\n"
        "CN-金額 - 記錄人民幣支出\n\n"
        "➖➖➖ 高級命令 ➖➖➖\n"
        "日期 TW+金額 - 記錄特定日期臺幣收入\n"
        "日期 TW-金額 - 記錄特定日期臺幣支出\n"
        "日期 CN+金額 - 記錄特定日期人民幣收入\n"
        "日期 CN-金額 - 記錄特定日期人民幣支出\n\n"
        "公桶+金額 - 記錄公桶資金增加\n"
        "公桶-金額 - 記錄公桶資金減少\n"
        "私人+金額 - 記錄私人資金增加\n"
        "私人-金額 - 記錄私人資金減少\n\n"
        "➖➖➖ M8P總表 ➖➖➖\n"
        "總表 - 顯示所有用戶合計報表\n"
        "總表 YYYY-MM - 顯示特定月份合計報表\n"
        "總表資金 - 查看總表資金狀態\n"
        "總表公桶=數字 - 設置總表公桶資金\n"
        "總表私人=數字 - 設置總表私人資金\n\n"
        "➖➖➖ 設定命令 ➖➖➖\n"
        "設置今日匯率33.25 - 設定今日匯率\n"
        "設置\"05/01\"匯率33.44 - 設定特定日期匯率\n"
        "報表使用者設定 名稱 - 設定報表名稱\n\n"
        "➖➖➖ 刪除命令 ➖➖➖\n"
        "刪除\"05/01\"NTD金額 - 刪除特定日期臺幣金額\n"
        "刪除\"05/01\"CNY金額 - 刪除特定日期人民幣金額\n\n"
        "➖➖➖ 其他功能 ➖➖➖\n"
        "📊查看本月報表 - 顯示當月報表\n"
        "📚歷史報表 - 查看過去月份報表\n"
    )
    bot.reply_to(message, help_text)

# 指令說明處理函數
@bot.message_handler(func=lambda message: message.text == '📋指令說明')
@error_handler
def handle_command_help(message):
    """處理指令說明請求"""
    help_text = """<b>📋 指令說明</b>

<b>🔸 基本指令</b>
/start - 啟動機器人，顯示主選單
/help - 顯示此幫助信息
/restart - 重新啟動機器人（僅管理員）

<b>🔸 報表指令</b>
📊查看本月報表 - 顯示當月收支報表
📚歷史報表 - 查看過去月份的報表
初始化報表 - 清空所有個人報表數據

<b>🔸 記帳指令 (可直接發送或點擊按鈕回覆)</b>
<code>TW+數字</code> - 記錄台幣收入
<code>TW-數字</code> - 記錄台幣支出
<code>CN+數字</code> - 記錄人民幣收入
<code>CN-數字</code> - 記錄人民幣支出

<b>🔸 日期記帳</b>
<code>日期 TW+數字</code> - 記錄特定日期台幣收入
<code>日期 TW-數字</code> - 記錄特定日期台幣支出
<code>日期 CN+數字</code> - 記錄特定日期人民幣收入
<code>日期 CN-數字</code> - 記錄特定日期人民幣支出

<b>🔸 為其他用戶記帳</b>
<code>@用戶名 日期 TW+數字</code> - 為指定用戶記錄台幣收入
<code>@用戶名 日期 TW-數字</code> - 為指定用戶記錄台幣支出
<code>@用戶名 日期 CN+數字</code> - 為指定用戶記錄人民幣收入
<code>@用戶名 日期 CN-數字</code> - 為指定用戶記錄人民幣支出

<b>🔸 資金管理</b>
<code>公桶+數字</code> - 增加公桶資金
<code>公桶-數字</code> - 減少公桶資金
<code>私人+數字</code> - 增加私人資金
<code>私人-數字</code> - 減少私人資金

<b>🔸 M8P總表</b>
<code>總表</code> - 顯示所有用戶合計報表
<code>總表 YYYY-MM</code> - 顯示特定月份的合計報表
<code>總表資金</code> - 查看總表資金狀態
<code>總表公桶=數字</code> - 設置總表公桶資金（管理員專用）
<code>總表私人=數字</code> - 設置總表私人資金（管理員專用）

<b>🔸 匯率設置</b>
<code>設置今日匯率數字</code> - 設置今日匯率
<code>設置"日期"匯率數字</code> - 設置指定日期匯率

<b>🔸 刪除記錄</b>
<code>刪除"日期"NTD金額</code> - 刪除指定日期台幣記錄
<code>刪除"日期"CNY金額</code> - 刪除指定日期人民幣記錄
<code>刪除"月份"NTD報表</code> - 刪除整個月份的台幣記錄 (格式: YYYY-MM 或 MM/YYYY)
<code>刪除"月份"CNY報表</code> - 刪除整個月份的人民幣記錄 (格式: YYYY-MM 或 MM/YYYY)

<b>🔸 其他設置</b>
<code>報表使用者設定 名稱</code> - 設置報表標題名稱

<b>🔸 群組管理</b>
⚙️群管設定 - 開啟群組管理選單"""

    bot.reply_to(message, help_text, parse_mode='HTML')
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了指令說明")

# 創建群管設定鍵盤
def create_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        KeyboardButton('👋 歡迎詞設定'),
        KeyboardButton('🔕 靜音設定')
    )
    keyboard.row(
        KeyboardButton('🧹 清理訊息'),
        KeyboardButton('🔒 權限管理')
    )
    keyboard.row(
        KeyboardButton('👤 成員管理'),
        KeyboardButton('⚠️ 警告系統')
    )
    keyboard.row(
        KeyboardButton('🔙 返回主選單')
    )
    return keyboard

# 群管設定處理函數
@bot.message_handler(func=lambda message: message.text == '⚙️群管設定')
@error_handler
def handle_admin_settings(message):
    """處理群管設定請求"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    admin_help_text = """<b>⚙️ 群組管理設定</b>

請選擇要管理的功能：

<b>👋 歡迎詞設定</b>
設置新成員加入群組時的歡迎訊息。

<b>🔕 靜音設定</b>
管理用戶禁言設置，可臨時或永久禁言。

<b>🧹 清理訊息</b>
批量刪除群組訊息，可刪除全部或特定時間段。

<b>🔒 權限管理</b>
設置用戶權限，管理操作員名單。

<b>👤 成員管理</b>
踢出成員、邀請用戶等成員管理功能。

<b>⚠️ 警告系統</b>
對違規用戶發出警告，達到上限自動禁言。

使用方式：點擊相應按鈕進入對應設定頁面。"""

    bot.reply_to(message, admin_help_text, parse_mode='HTML', reply_markup=create_admin_keyboard())
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 進入群組管理設定")

# 處理返回主選單
@bot.message_handler(func=lambda message: message.text == '🔙 返回主選單')
@error_handler
def handle_return_to_main(message):
    """處理返回主選單請求"""
    bot.reply_to(message, "✅ 已返回主選單", reply_markup=create_keyboard())
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 返回主選單")

# 歡迎詞設定
@bot.message_handler(func=lambda message: message.text == '👋 歡迎詞設定')
@error_handler
def handle_welcome_settings(message):
    """處理歡迎詞設定請求"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 獲取當前歡迎詞
    settings = load_data(USER_SETTINGS_FILE)
    chat_id = str(message.chat.id)
    
    # 從配置中獲取當前歡迎詞，如果沒有則使用預設值
    current_welcome = "歡迎 {USERNAME} 加入 {GROUPNAME}！"
    if chat_id in settings and 'welcome_message' in settings[chat_id]:
        current_welcome = settings[chat_id]['welcome_message']
    
    welcome_help_text = f"""<b>👋 歡迎詞設定</b>

當前歡迎詞：
<pre>{current_welcome}</pre>

可用變數：
<code>{{USERNAME}}</code> - 新成員的用戶名
<code>{{FULLNAME}}</code> - 新成員的完整名稱
<code>{{FIRSTNAME}}</code> - 新成員的名字
<code>{{GROUPNAME}}</code> - 群組名稱

設定方式：
直接回覆此訊息，輸入新的歡迎詞內容即可。"""

    # 儲存用戶狀態
    sent_msg = bot.reply_to(message, welcome_help_text, parse_mode='HTML')
    user_states[message.from_user.id] = {
        'state': 'waiting_welcome_message', 
        'chat_id': message.chat.id,
        'prompt_msg_id': sent_msg.message_id
    }
    
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 查看歡迎詞設定")

# 處理歡迎詞設定回覆
@bot.message_handler(func=lambda message: message.reply_to_message is not None and 
                                          message.from_user.id in user_states and 
                                          user_states[message.from_user.id].get('state') == 'waiting_welcome_message' and
                                          user_states[message.from_user.id].get('prompt_msg_id') == message.reply_to_message.message_id)
@error_handler
def handle_welcome_message_reply(message):
    """處理用戶對歡迎詞設定的回覆"""
    user_id = message.from_user.id
    chat_id = user_states[user_id]['chat_id']
    
    # 獲取歡迎詞內容
    welcome_message = message.text.strip()
    
    try:
        # 保存歡迎詞設定
        settings = load_data(USER_SETTINGS_FILE)
        
        # 使用聊天ID作為鍵，以便群組特定設定
        chat_id_str = str(chat_id)
        if chat_id_str not in settings:
            settings[chat_id_str] = {}
        
        settings[chat_id_str]['welcome_message'] = welcome_message
        save_data(settings, USER_SETTINGS_FILE)
        
        # 回覆成功訊息
        bot.reply_to(message, f"✅ 歡迎詞已成功設定為：\n\n<pre>{welcome_message}</pre>", parse_mode='HTML')
        logger.info(f"管理員 {message.from_user.username or user_id} 設定了新的歡迎詞")
    except Exception as e:
        bot.reply_to(message, f"❌ 設定歡迎詞時出錯：{str(e)}")
        logger.error(f"設定歡迎詞出錯: {str(e)}")
    
    # 清除用戶狀態
    if user_id in user_states:
        del user_states[user_id]

# 靜音設定
@bot.message_handler(func=lambda message: message.text == '🔕 靜音設定')
@error_handler
def handle_mute_settings(message):
    """處理靜音設定請求"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    mute_help_text = """<b>🔕 靜音設定</b>

禁言用戶的指令：
<code>/ban @用戶名 [時間] [原因]</code>
例如：<code>/ban @user 24h 違反規定</code>

時間格式：
- <code>1h</code>：1小時
- <code>1d</code>：1天
- <code>1w</code>：1週
不指定時間則為永久禁言

解除禁言：
<code>/unban @用戶名</code>

注意：
1. 只有管理員可以使用此功能
2. 無法禁言其他管理員
3. 只有群主可以禁言管理員"""

    bot.reply_to(message, mute_help_text, parse_mode='HTML')
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 查看靜音設定")

# 清理訊息
@bot.message_handler(func=lambda message: message.text == '🧹 清理訊息')
@error_handler
def handle_clear_messages(message):
    """處理清理訊息請求"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    clear_help_text = """<b>🧹 清理訊息</b>

清理訊息的指令：

<code>/del</code> - 回覆要刪除的訊息以刪除單一訊息
<code>刪除所有聊天室訊息</code> - 刪除所有訊息（慎用）
<code>刪除所有非置頂訊息</code> - 保留置頂訊息，刪除其他訊息

注意：
1. 只有管理員可以使用此功能
2. 一次大量刪除可能耗時較長
3. 機器人需要擁有刪除訊息的權限"""

    bot.reply_to(message, clear_help_text, parse_mode='HTML')
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 查看清理訊息設定")

# 權限管理
@bot.message_handler(func=lambda message: message.text == '🔒 權限管理')
@error_handler
def handle_permission_settings(message):
    """處理權限管理請求"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    permission_help_text = """<b>🔒 權限管理</b>

操作員管理指令：

<code>設定操作員 @用戶名1 @用戶名2 ...</code> - 設定操作員
<code>查看操作員</code> - 列出所有操作員
<code>刪除操作員 @用戶名1 @用戶名2 ...</code> - 移除操作員

查看權限指令：
<code>/info @用戶名</code> - 查看用戶在群組中的權限狀態

注意：
1. 操作員可以使用記帳和設定匯率功能
2. 只有管理員可以設定操作員
3. 操作員不具備群組管理權限"""

    bot.reply_to(message, permission_help_text, parse_mode='HTML')
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 查看權限管理設定")

# 成員管理
@bot.message_handler(func=lambda message: message.text == '👤 成員管理')
@error_handler
def handle_member_management(message):
    """處理成員管理請求"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    member_help_text = """<b>👤 成員管理</b>

成員管理指令：

<code>/kick @用戶名 [原因]</code> - 踢出用戶
例如：<code>/kick @user 違反規定</code>

<code>/admin</code> - 查看管理員命令列表

<code>📋查看管理員</code> - 列出所有群組管理員

注意：
1. 只有管理員可以使用此功能
2. 無法踢出其他管理員
3. 被踢出的用戶依然可以透過邀請連結重新加入"""

    bot.reply_to(message, member_help_text, parse_mode='HTML')
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 查看成員管理設定")

# 警告系統
@bot.message_handler(func=lambda message: message.text == '⚠️ 警告系統')
@error_handler
def handle_warning_system(message):
    """處理警告系統請求"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    warning_help_text = """<b>⚠️ 警告系統</b>

警告系統指令：

<code>/warn @用戶名 [原因]</code> - 警告用戶
例如：<code>/warn @user 違反規定</code>

<code>/unwarn @用戶名</code> - 移除用戶警告

<code>/warns @用戶名</code> - 查看用戶警告次數

注意：
1. 只有管理員可以使用此功能
2. 無法警告其他管理員
3. 警告達到3次將自動禁言24小時
4. 禁言後警告次數會被重置"""

    bot.reply_to(message, warning_help_text, parse_mode='HTML')
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 查看警告系統設定")

# 刪除指定月份的NTD報表記錄
@bot.message_handler(regexp=r'^刪除"([0-9/\-]+)"NTD報表$')
@error_handler
def handle_delete_month_ntd(message):
    """刪除指定月份的台幣記錄"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限管理員使用")
        return
    
    match = re.match(r'^刪除"([0-9/\-]+)"NTD報表$', message.text)
    month_str = match.group(1)
    
    try:
        # 處理不同的日期格式
        if '/' in month_str:
            parts = month_str.split('/')
            if len(parts) == 2:
                month, year = int(parts[0]), int(parts[1])
            else:
                raise ValueError("月份格式不正確")
        elif '-' in month_str:
            parts = month_str.split('-')
            if len(parts) == 2:
                year, month = int(parts[0]), int(parts[1])
            else:
                raise ValueError("月份格式不正確")
        else:
            raise ValueError("月份格式不正確")
        
        # 計算月份的日期範圍
        _, last_day = calendar.monthrange(year, month)
        month_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
        
        # 刪除該月份的所有台幣記錄
        data = load_data(DATA_FILE)
        user_id = str(message.from_user.id)
        
        if user_id not in data:
            bot.reply_to(message, "❌ 您還沒有任何記錄")
            return
        
        deleted_count = 0
        for date in month_dates:
            if date in data[user_id] and "TW" in data[user_id][date]:
                data[user_id][date]["TW"] = 0
                deleted_count += 1
        
        save_data(data, DATA_FILE)
        
        bot.reply_to(message, f"✅ 已刪除 {year}年{month}月 的 {deleted_count} 筆台幣記錄")
        logger.info(f"用戶 {message.from_user.username or message.from_user.id} 刪除了 {year}年{month}月 的台幣記錄")
    
    except Exception as e:
        bot.reply_to(message, f"❌ 刪除失敗: {str(e)}\n格式應為 MM/YYYY 或 YYYY-MM")
        logger.error(f"刪除月份資料失敗: {str(e)}")

# 刪除指定月份的CNY報表記錄
@bot.message_handler(regexp=r'^刪除"([0-9/\-]+)"CNY報表$')
@error_handler
def handle_delete_month_cny(message):
    """刪除指定月份的人民幣記錄"""
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限管理員使用")
        return
    
    match = re.match(r'^刪除"([0-9/\-]+)"CNY報表$', message.text)
    month_str = match.group(1)
    
    try:
        # 處理不同的日期格式
        if '/' in month_str:
            parts = month_str.split('/')
            if len(parts) == 2:
                month, year = int(parts[0]), int(parts[1])
            else:
                raise ValueError("月份格式不正確")
        elif '-' in month_str:
            parts = month_str.split('-')
            if len(parts) == 2:
                year, month = int(parts[0]), int(parts[1])
            else:
                raise ValueError("月份格式不正確")
        else:
            raise ValueError("月份格式不正確")
        
        # 計算月份的日期範圍
        _, last_day = calendar.monthrange(year, month)
        month_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
        
        # 刪除該月份的所有人民幣記錄
        data = load_data(DATA_FILE)
        user_id = str(message.from_user.id)
        
        if user_id not in data:
            bot.reply_to(message, "❌ 您還沒有任何記錄")
            return
        
        deleted_count = 0
        for date in month_dates:
            if date in data[user_id] and "CN" in data[user_id][date]:
                data[user_id][date]["CN"] = 0
                deleted_count += 1
        
        save_data(data, DATA_FILE)
        
        bot.reply_to(message, f"✅ 已刪除 {year}年{month}月 的 {deleted_count} 筆人民幣記錄")
        logger.info(f"用戶 {message.from_user.username or message.from_user.id} 刪除了 {year}年{month}月 的人民幣記錄")
    
    except Exception as e:
        bot.reply_to(message, f"❌ 刪除失敗: {str(e)}\n格式應為 MM/YYYY 或 YYYY-MM")
        logger.error(f"刪除月份資料失敗: {str(e)}")

# 初始化報表功能
@bot.message_handler(func=lambda message: message.text == '初始化報表')
@error_handler
def handle_initialize_report(message):
    """初始化用戶的報表數據"""
    user_id = message.from_user.id
    
    # 記錄請求
    logger.info(f"用戶 {message.from_user.username or user_id} 請求初始化報表")
    
    try:
        # 檢查用戶是否已有狀態，如果有則清除
        if user_id in user_states:
            logger.info(f"清除用戶 {user_id} 之前的狀態: {user_states[user_id]}")
            del user_states[user_id]
        
        # 確認操作
        msg = bot.reply_to(message, "⚠️ 此操作將刪除您的所有記帳資料，確定要初始化嗎？\n\n請回覆「確認初始化」來繼續，或回覆其他內容取消。")
        
        # 儲存用戶狀態
        user_states[user_id] = {
            'state': 'waiting_init_confirmation',
            'prompt_msg_id': msg.message_id
        }
        
        logger.info(f"已設置用戶 {user_id} 的狀態: {user_states[user_id]}")
    except Exception as e:
        error_msg = f"處理初始化報表請求時出錯: {str(e)}"
        logger.error(error_msg)
        bot.reply_to(message, f"❌ 處理初始化報表請求時出錯: {str(e)}")

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

# 群管功能按鈕實現
# 創建群管功能鍵盤
def create_admin_function_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👋 設置歡迎詞", callback_data="admin_welcome"),
        InlineKeyboardButton("🔕 禁言管理", callback_data="admin_mute")
    )
    keyboard.add(
        InlineKeyboardButton("🧹 清理消息", callback_data="admin_clean"),
        InlineKeyboardButton("🔒 權限設置", callback_data="admin_perm")
    )
    keyboard.add(
        InlineKeyboardButton("👤 成員管理", callback_data="admin_member"),
        InlineKeyboardButton("⚠️ 警告系統", callback_data="admin_warn")
    )
    keyboard.add(
        InlineKeyboardButton("🔙 返回主選單", callback_data="admin_back")
    )
    return keyboard

# 更新群管設定處理函數
@bot.message_handler(func=lambda message: message.text == '⚙️群管設定')
@error_handler
def handle_admin_settings(message):
    """處理群管設定請求"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    admin_help_text = """<b>⚙️ 群組管理設定</b>

請選擇要管理的功能：

<b>👋 歡迎詞設定</b>
設置新成員加入群組時的歡迎訊息。

<b>🔕 靜音設定</b>
管理用戶禁言設置，可臨時或永久禁言。

<b>🧹 清理訊息</b>
批量刪除群組訊息，可刪除全部或特定時間段。

<b>🔒 權限管理</b>
設置用戶權限，管理操作員名單。

<b>👤 成員管理</b>
踢出成員、邀請用戶等成員管理功能。

<b>⚠️ 警告系統</b>
對違規用戶發出警告，達到上限自動禁言。

使用方式：點擊相應按鈕進入對應設定頁面。"""

    bot.reply_to(message, admin_help_text, parse_mode='HTML', reply_markup=create_admin_function_keyboard())
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 進入群組管理設定")

# 處理群管功能按鈕回調
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
@error_handler
def handle_admin_callback(call):
    """處理群管按鈕回調"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # 檢查是否為管理員
    if not is_admin(user_id, chat_id):
        bot.answer_callback_query(call.id, "❌ 此功能僅限群組管理員使用", show_alert=True)
        return
    
    action = call.data[6:]  # 移除 'admin_' 前綴
    
    if action == "welcome":
        # 歡迎詞設定
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="""<b>👋 歡迎詞設定</b>

當前歡迎詞：
<pre>歡迎 {{USERNAME}} 加入 {{GROUPNAME}}！</pre>

可用變數：
<code>{{USERNAME}}</code> - 新成員的用戶名
<code>{{FULLNAME}}</code> - 新成員的完整名稱
<code>{{FIRSTNAME}}</code> - 新成員的名字
<code>{{GROUPNAME}}</code> - 群組名稱

設定方式：
請在群組中直接發送：
<code>設定歡迎詞：您要設定的歡迎詞內容</code>""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 返回", callback_data="admin_back")
            )
        )
    
    elif action == "mute":
        # 禁言管理
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="""<b>🔕 靜音設定</b>

禁言用戶的指令：
<code>/ban @用戶名 [時間] [原因]</code>
例如：<code>/ban @user 24h 違反規定</code>

時間格式：
- <code>1h</code>：1小時
- <code>1d</code>：1天
- <code>1w</code>：1週
不指定時間則為永久禁言

解除禁言：
<code>/unban @用戶名</code>""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 返回", callback_data="admin_back")
            )
        )
    
    elif action == "clean":
        # 清理消息
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="""<b>🧹 清理訊息</b>

清理訊息的指令：

<code>/del</code> - 回覆要刪除的訊息以刪除單一訊息
<code>刪除所有聊天室訊息</code> - 刪除所有訊息（慎用）
<code>刪除所有非置頂訊息</code> - 保留置頂訊息，刪除其他訊息""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 返回", callback_data="admin_back")
            )
        )
    
    elif action == "perm":
        # 權限設置
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="""<b>🔒 權限管理</b>

操作員管理指令：

<code>設定操作員 @用戶名1 @用戶名2 ...</code> - 設定操作員
<code>查看操作員</code> - 列出所有操作員
<code>刪除操作員 @用戶名1 @用戶名2 ...</code> - 移除操作員

查看權限指令：
<code>/info @用戶名</code> - 查看用戶在群組中的權限狀態""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 返回", callback_data="admin_back")
            )
        )
    
    elif action == "member":
        # 成員管理
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="""<b>👤 成員管理</b>

成員管理指令：

<code>/kick @用戶名 [原因]</code> - 踢出用戶
例如：<code>/kick @user 違反規定</code>

<code>/admin</code> - 查看管理員命令列表

<code>📋查看管理員</code> - 列出所有群組管理員""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 返回", callback_data="admin_back")
            )
        )
    
    elif action == "warn":
        # 警告系統
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="""<b>⚠️ 警告系統</b>

警告系統指令：

<code>/warn @用戶名 [原因]</code> - 警告用戶
例如：<code>/warn @user 違反規定</code>

<code>/unwarn @用戶名</code> - 移除用戶警告

<code>/warns @用戶名</code> - 查看用戶警告次數""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 返回", callback_data="admin_back")
            )
        )
    
    elif action == "back":
        # 返回主選單
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, "✅ 已返回主選單", reply_markup=create_keyboard())
    
    # 回答回調查詢
    bot.answer_callback_query(call.id)

# 啟動時啟動定期清理任務
if __name__ == '__main__':
    try:
        logger.info("機器人啟動中...")
        BOT_START_TIME = datetime.now()
        
        # 初始化數據文件
        init_files()
        
        # 檢查是重啟還是新啟動
        is_restart = False
        if os.path.exists("restart_flag.txt"):
            is_restart = True
            os.remove("restart_flag.txt")  # 移除標記文件
        
        # 清理舊數據
        clean_old_data()
        
        # 啟動心跳檢測
        start_heartbeat()
        
        # 發送啟動/重啟通知到群組
        if is_restart:
            # 重啟通知
            try:
                bot.send_message(TARGET_GROUP_ID, "✅ 機器人已重新啟動完成，可以繼續使用！")
                logger.info(f"已發送重啟完成通知到群組 {TARGET_GROUP_ID}")
            except Exception as e:
                logger.error(f"發送重啟完成通知失敗: {str(e)}")
        else:
            # 新啟動通知
            send_startup_notification()
        
        # 啟動機器人
        logger.info("機器人開始監聽消息...")
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        logger.critical(f"機器人啟動失敗: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1) 

# 處理新成員加入
@bot.message_handler(content_types=['new_chat_members'])
@error_handler
def handle_new_members(message):
    """處理新成員加入群組事件"""
    chat_id = message.chat.id
    
    # 獲取設定的歡迎詞
    settings = load_data(USER_SETTINGS_FILE)
    chat_id_str = str(chat_id)
    
    # 默認歡迎詞
    welcome_message = "歡迎 {USERNAME} 加入 {GROUPNAME}！"
    
    # 如果有設定的歡迎詞，使用設定的
    if chat_id_str in settings and 'welcome_message' in settings[chat_id_str]:
        welcome_message = settings[chat_id_str]['welcome_message']
    
    # 獲取群組名稱
    group_name = message.chat.title
    
    # 處理每個新成員
    for new_member in message.new_chat_members:
        # 跳過機器人自己
        if new_member.id == bot.get_me().id:
            continue
        
        # 使用變數替換歡迎詞中的佔位符
        username = new_member.username if new_member.username else new_member.first_name
        formatted_message = welcome_message.format(
            USERNAME=f"@{username}" if new_member.username else username,
            FULLNAME=f"{new_member.first_name} {new_member.last_name if new_member.last_name else ''}",
            FIRSTNAME=new_member.first_name,
            GROUPNAME=group_name
        )
        
        # 發送歡迎訊息
        bot.send_message(chat_id, formatted_message, parse_mode='HTML')
        
        # 記錄日誌
        logger.info(f"歡迎新成員 {username} 加入群組 {group_name}")

@bot.message_handler(func=lambda message: message.text and message.text.strip() == '刪除所有聊天室訊息', content_types=['text'])
@error_handler
def handle_delete_all_messages(message):
    """處理刪除所有聊天室訊息的請求"""
    logger.info(f"收到刪除所有聊天室訊息請求，來自用戶 {message.from_user.username or message.from_user.id}，消息內容：'{message.text}'")
    
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        logger.warning(f"用戶 {message.from_user.username or message.from_user.id} 嘗試使用刪除所有訊息功能但不是管理員")
        return
    
    # 發送確認訊息，避免誤操作
    try:
        logger.info(f"準備發送確認訊息給管理員 {message.from_user.username or message.from_user.id}")
        confirm_msg = bot.reply_to(
            message, 
            "⚠️ <b>警告</b>：此操作將刪除聊天中的<b>所有訊息</b>，確定要執行嗎？\n\n"
            "請回覆「確認刪除所有訊息」來確認此操作。",
            parse_mode='HTML'
        )
        
        # 儲存用戶狀態
        user_states[message.from_user.id] = {
            'state': 'waiting_delete_all_confirmation',
            'chat_id': message.chat.id,
            'prompt_msg_id': confirm_msg.message_id
        }
        
        logger.info(f"管理員 {message.from_user.username or message.from_user.id} 請求刪除所有聊天室訊息，等待確認，message_id={confirm_msg.message_id}")
    except Exception as e:
        logger.error(f"發送確認訊息時出錯: {e}")
        bot.reply_to(message, f"❌ 發送確認訊息時出錯: {str(e)}")

# 刪除所有非置頂訊息
@bot.message_handler(func=lambda message: message.text and message.text.strip() == '刪除所有非置頂訊息', content_types=['text'])
@error_handler
def handle_delete_non_pinned_messages(message):
    """處理刪除所有非置頂訊息的請求"""
    logger.info(f"收到刪除所有非置頂訊息請求，來自用戶 {message.from_user.username or message.from_user.id}，消息內容：'{message.text}'")
    
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        logger.warning(f"用戶 {message.from_user.username or message.from_user.id} 嘗試使用刪除非置頂訊息功能但不是管理員")
        return
    
    # 發送確認訊息，避免誤操作
    try:
        logger.info(f"準備發送確認訊息給管理員 {message.from_user.username or message.from_user.id}")
        confirm_msg = bot.reply_to(
            message, 
            "⚠️ <b>警告</b>：此操作將刪除聊天中的<b>所有非置頂訊息</b>，確定要執行嗎？\n\n"
            "請回覆「確認刪除非置頂訊息」來確認此操作。",
            parse_mode='HTML'
        )
        
        # 儲存用戶狀態
        user_states[message.from_user.id] = {
            'state': 'waiting_delete_non_pinned_confirmation',
            'chat_id': message.chat.id,
            'prompt_msg_id': confirm_msg.message_id
        }
        
        logger.info(f"管理員 {message.from_user.username or message.from_user.id} 請求刪除所有非置頂訊息，等待確認，message_id={confirm_msg.message_id}")
    except Exception as e:
        logger.error(f"發送確認訊息時出錯: {e}")
        bot.reply_to(message, f"❌ 發送確認訊息時出錯: {str(e)}")

# 刪除單一訊息
@bot.message_handler(commands=['del'])
@error_handler
def handle_delete_single_message(message):
    """處理刪除單一訊息的請求"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 檢查是否回覆了訊息
    if not message.reply_to_message:
        bot.reply_to(message, "❌ 請回覆要刪除的訊息使用此命令")
        return
    
    try:
        # 刪除被回覆的訊息
        bot.delete_message(message.chat.id, message.reply_to_message.message_id)
        # 刪除命令訊息
        bot.delete_message(message.chat.id, message.message_id)
        logger.info(f"管理員 {message.from_user.username or message.from_user.id} 刪除了一條訊息")
    except Exception as e:
        bot.reply_to(message, f"❌ 刪除訊息失敗：{str(e)}")
        logger.error(f"刪除訊息失敗: {str(e)}")

# 處理刪除所有訊息確認
@bot.message_handler(func=lambda message: message.reply_to_message is not None and 
                                          message.from_user.id in user_states and 
                                          user_states[message.from_user.id].get('state') == 'waiting_delete_all_confirmation' and
                                          user_states[message.from_user.id].get('prompt_msg_id') == message.reply_to_message.message_id)
@error_handler
def handle_delete_all_confirmation(message):
    """處理用戶對刪除所有訊息的確認"""
    user_id = message.from_user.id
    chat_id = user_states[user_id]['chat_id']
    
    logger.info(f"收到刪除所有訊息的確認回覆，來自用戶 {message.from_user.username or user_id}，內容：'{message.text}'")
    logger.info(f"用戶狀態：{user_states[user_id]}")
    logger.info(f"回覆的訊息ID：{message.reply_to_message.message_id}")
    
    if message.text.strip() == '確認刪除所有訊息':
        # 發送開始刪除的通知
        status_msg = bot.reply_to(message, "🔄 開始刪除所有訊息，這可能需要一些時間...")
        logger.info(f"開始執行刪除所有訊息，來自管理員 {message.from_user.username or user_id}")
        
        try:
            # 獲取群組中的所有訊息（實際上需要使用API，這裡是簡化示例）
            # 由於API限制，實際操作可能需要更複雜的方法
            messages_deleted = 0
            
            # 刪除最近的訊息
            # 這裡只能示意性刪除，因為Telegram API不允許批量刪除所有訊息
            # 實際應用需要獲取訊息ID列表並逐一刪除
            for i in range(message.message_id, message.message_id - 100, -1):
                try:
                    bot.delete_message(chat_id, i)
                    messages_deleted += 1
                    if messages_deleted % 10 == 0:
                        logger.info(f"已刪除 {messages_deleted} 條訊息")
                except Exception as e:
                    logger.debug(f"刪除訊息 ID {i} 失敗: {str(e)}")
            
            # 更新狀態訊息
            try:
                bot.edit_message_text(
                    f"✅ 操作完成，已嘗試刪除 {messages_deleted} 條訊息。\n"
                    f"注意：由於Telegram限制，僅能刪除最近的訊息。",
                    chat_id=chat_id,
                    message_id=status_msg.message_id
                )
                logger.info(f"已更新刪除狀態訊息，刪除數量：{messages_deleted}")
            except Exception as e:
                logger.error(f"更新狀態訊息失敗: {str(e)}")
            
            logger.info(f"管理員 {message.from_user.username or user_id} 刪除了 {messages_deleted} 條訊息")
            
        except Exception as e:
            error_msg = f"❌ 刪除訊息時出錯：{str(e)}"
            bot.reply_to(message, error_msg)
            logger.error(f"批量刪除訊息出錯: {str(e)}")
    else:
        bot.reply_to(message, "❌ 操作已取消")
        logger.info(f"管理員 {message.from_user.username or user_id} 取消了刪除所有訊息")
    
    # 清除用戶狀態
    if user_id in user_states:
        del user_states[user_id]
        logger.info(f"已清除用戶 {message.from_user.username or user_id} 的狀態")

# 處理刪除非置頂訊息確認
@bot.message_handler(func=lambda message: message.reply_to_message is not None and 
                                          message.from_user.id in user_states and 
                                          user_states[message.from_user.id].get('state') == 'waiting_delete_non_pinned_confirmation' and
                                          user_states[message.from_user.id].get('prompt_msg_id') == message.reply_to_message.message_id)
@error_handler
def handle_delete_non_pinned_confirmation(message):
    """處理用戶對刪除非置頂訊息的確認"""
    user_id = message.from_user.id
    chat_id = user_states[user_id]['chat_id']
    
    logger.info(f"收到刪除非置頂訊息的確認回覆，來自用戶 {message.from_user.username or user_id}，內容：'{message.text}'")
    logger.info(f"用戶狀態：{user_states[user_id]}")
    logger.info(f"回覆的訊息ID：{message.reply_to_message.message_id}")
    
    if message.text.strip() == '確認刪除非置頂訊息':
        # 發送開始刪除的通知
        status_msg = bot.reply_to(message, "🔄 開始刪除所有非置頂訊息，這可能需要一些時間...")
        logger.info(f"開始執行刪除非置頂訊息，來自管理員 {message.from_user.username or user_id}")
        
        try:
            # 獲取置頂訊息ID
            pinned_message = None
            try:
                pinned_message = bot.get_chat(chat_id).pinned_message
                logger.info(f"置頂訊息 ID: {pinned_message.message_id if pinned_message else '無'}")
            except Exception as e:
                logger.error(f"獲取置頂訊息時出錯: {str(e)}")
                pass
            
            pinned_id = pinned_message.message_id if pinned_message else -1
            
            # 刪除最近的非置頂訊息
            messages_deleted = 0
            
            for i in range(message.message_id, message.message_id - 100, -1):
                if i != pinned_id:
                    try:
                        bot.delete_message(chat_id, i)
                        messages_deleted += 1
                        if messages_deleted % 10 == 0:
                            logger.info(f"已刪除 {messages_deleted} 條非置頂訊息")
                    except Exception as e:
                        logger.debug(f"刪除訊息 ID {i} 失敗: {str(e)}")
            
            # 更新狀態訊息
            try:
                bot.edit_message_text(
                    f"✅ 操作完成，已嘗試刪除 {messages_deleted} 條非置頂訊息。\n"
                    f"注意：由於Telegram限制，僅能刪除最近的訊息。",
                    chat_id=chat_id,
                    message_id=status_msg.message_id
                )
                logger.info(f"已更新刪除狀態訊息，刪除數量：{messages_deleted}")
            except Exception as e:
                logger.error(f"更新狀態訊息失敗: {str(e)}")
            
            logger.info(f"管理員 {message.from_user.username or user_id} 刪除了 {messages_deleted} 條非置頂訊息")
            
        except Exception as e:
            error_msg = f"❌ 刪除訊息時出錯：{str(e)}"
            bot.reply_to(message, error_msg)
            logger.error(f"批量刪除非置頂訊息出錯: {str(e)}")
    else:
        bot.reply_to(message, "❌ 操作已取消")
        logger.info(f"管理員 {message.from_user.username or user_id} 取消了刪除非置頂訊息")
    
    # 清除用戶狀態
    if user_id in user_states:
        del user_states[user_id]
        logger.info(f"已清除用戶 {message.from_user.username or user_id} 的狀態")

# 處理 /ban 指令
@bot.message_handler(commands=['ban'])
@error_handler
def handle_ban_command(message):
    """處理禁言用戶的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 解析命令參數
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args:
        bot.reply_to(message, "❌ 使用方式: /ban @用戶名 [時間] [原因]\n例如: /ban @user 24h 違反規定")
        return
    
    # 解析目標用戶
    target_username = command_args[0].replace('@', '')
    
    # 尋找目標用戶ID
    target_user_id = None
    try:
        # 如果是回覆某人的訊息
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or f"ID:{target_user_id}"
        else:
            # 從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == target_username:
                    target_user_id = member.user.id
                    break
            
            # 如果未找到，嘗試使用正則表達式解析數字ID
            if not target_user_id and command_args[0].isdigit():
                target_user_id = int(command_args[0])
    except Exception as e:
        bot.reply_to(message, f"❌ 尋找目標用戶時出錯: {str(e)}")
        logger.error(f"尋找目標用戶出錯: {str(e)}")
        return
    
    if not target_user_id:
        bot.reply_to(message, f"❌ 找不到用戶 '{target_username}'")
        return
    
    # 檢查目標用戶是否為管理員
    if is_admin(target_user_id, message.chat.id):
        # 如果目標是管理員，檢查操作者是否為群主
        try:
            chat_creator = None
            chat_info = bot.get_chat(message.chat.id)
            if hasattr(chat_info, 'owner_id'):
                chat_creator = chat_info.owner_id
            
            # 如果操作者不是群主，禁止禁言其他管理員
            if message.from_user.id != chat_creator:
                bot.reply_to(message, "❌ 您無法禁言其他管理員，只有群主可以進行此操作")
                return
        except:
            bot.reply_to(message, "❌ 無法禁言其他管理員")
            return
    
    # 解析禁言時間
    ban_time = None
    reason = "未指定原因"
    
    if len(command_args) > 1:
        time_arg = command_args[1].lower()
        
        # 解析時間格式
        if time_arg.endswith('h'):
            try:
                hours = int(time_arg[:-1])
                ban_time = timedelta(hours=hours)
            except:
                pass
        elif time_arg.endswith('d'):
            try:
                days = int(time_arg[:-1])
                ban_time = timedelta(days=days)
            except:
                pass
        elif time_arg.endswith('w'):
            try:
                weeks = int(time_arg[:-1])
                ban_time = timedelta(weeks=weeks)
            except:
                pass
    
    # 解析禁言原因
    if len(command_args) > 2:
        reason = ' '.join(command_args[2:])
    
    # 執行禁言
    try:
        # 計算禁言結束時間
        until_date = None
        if ban_time:
            until_date = int((datetime.now() + ban_time).timestamp())
        
        # 設置禁言權限
        bot.restrict_chat_member(
            message.chat.id, 
            target_user_id,
            permissions=telebot.types.ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            ),
            until_date=until_date
        )
        
        # 發送成功訊息
        if ban_time:
            time_str = f"{ban_time.days}天" if ban_time.days > 0 else f"{ban_time.seconds//3600}小時"
            bot.reply_to(message, f"✅ 已禁言用戶 {target_username} {time_str}\n原因: {reason}")
        else:
            bot.reply_to(message, f"✅ 已永久禁言用戶 {target_username}\n原因: {reason}")
        
        logger.info(f"管理員 {message.from_user.username or message.from_user.id} 禁言了用戶 {target_username}")
    
    except Exception as e:
        bot.reply_to(message, f"❌ 禁言用戶時出錯: {str(e)}")
        logger.error(f"禁言用戶出錯: {str(e)}")

# 處理 /unban 指令
@bot.message_handler(commands=['unban'])
@error_handler
def handle_unban_command(message):
    """處理解除禁言用戶的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 解析命令參數
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args:
        bot.reply_to(message, "❌ 使用方式: /unban @用戶名\n例如: /unban @user")
        return
    
    # 解析目標用戶
    target_username = command_args[0].replace('@', '')
    
    # 尋找目標用戶ID
    target_user_id = None
    try:
        # 如果是回覆某人的訊息
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or f"ID:{target_user_id}"
        else:
            # 從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == target_username:
                    target_user_id = member.user.id
                    break
            
            # 如果未找到，嘗試使用正則表達式解析數字ID
            if not target_user_id and command_args[0].isdigit():
                target_user_id = int(command_args[0])
    except Exception as e:
        bot.reply_to(message, f"❌ 尋找目標用戶時出錯: {str(e)}")
        logger.error(f"尋找目標用戶出錯: {str(e)}")
        return
    
    if not target_user_id:
        bot.reply_to(message, f"❌ 找不到用戶 '{target_username}'")
        return
    
    # 執行解除禁言
    try:
        # 設置完整權限
        bot.restrict_chat_member(
            message.chat.id, 
            target_user_id,
            permissions=telebot.types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        )
        
        # 發送成功訊息
        bot.reply_to(message, f"✅ 已解除禁言用戶 {target_username}")
        logger.info(f"管理員 {message.from_user.username or message.from_user.id} 解除了用戶 {target_username} 的禁言")
    except Exception as e:
        bot.reply_to(message, f"❌ 解除禁言用戶時出錯: {str(e)}")
        logger.error(f"解除禁言用戶出錯: {str(e)}")

# 處理設定操作員指令
@bot.message_handler(regexp=r'^設定操作員\s+(.+)$')
@error_handler
def handle_set_operators(message):
    """處理設定操作員的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 解析指令參數
    match = re.match(r'^設定操作員\s+(.+)$', message.text)
    if not match:
        bot.reply_to(message, "❌ 使用方式: 設定操作員 @用戶名1 @用戶名2 ...")
        return
    
    operators_text = match.group(1).strip()
    usernames = re.findall(r'@(\w+)', operators_text)
    
    if not usernames:
        bot.reply_to(message, "❌ 未指定任何用戶名。使用方式: 設定操作員 @用戶名1 @用戶名2 ...")
        return
    
    # 加載當前設定
    settings = load_data(USER_SETTINGS_FILE)
    
    # 獲取或創建群組設定
    chat_id_str = str(message.chat.id)
    if chat_id_str not in settings:
        settings[chat_id_str] = {}
    
    if 'operators' not in settings[chat_id_str]:
        settings[chat_id_str]['operators'] = {}
    
    # 查找用戶ID
    added_users = []
    not_found_users = []
    
    for username in usernames:
        user_id = None
        try:
            # 嘗試從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == username:
                    user_id = member.user.id
                    break
            
            # 如果找到用戶，添加到操作員列表
            if user_id:
                settings[chat_id_str]['operators'][str(user_id)] = {
                    'username': username,
                    'added_by': message.from_user.id,
                    'added_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                added_users.append(f"@{username}")
            else:
                not_found_users.append(f"@{username}")
        except Exception as e:
            logger.error(f"查找用戶 {username} 時出錯: {str(e)}")
            not_found_users.append(f"@{username}")
    
    # 保存設定
    save_data(settings, USER_SETTINGS_FILE)
    
    # 構建回覆訊息
    reply = ""
    if added_users:
        reply += f"✅ 已添加以下操作員:\n{', '.join(added_users)}\n"
    
    if not_found_users:
        reply += f"❌ 找不到以下用戶:\n{', '.join(not_found_users)}"
    
    bot.reply_to(message, reply.strip())
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 設定了操作員: {', '.join(added_users)}")

# 處理查看操作員指令
@bot.message_handler(func=lambda message: message.text == '查看操作員')
@error_handler
def handle_list_operators(message):
    """處理查看操作員的指令"""
    # 加載當前設定
    settings = load_data(USER_SETTINGS_FILE)
    
    # 獲取群組設定
    chat_id_str = str(message.chat.id)
    
    # 檢查是否有操作員設定
    if chat_id_str not in settings or 'operators' not in settings[chat_id_str] or not settings[chat_id_str]['operators']:
        bot.reply_to(message, "📝 當前沒有設定任何操作員")
        return
    
    # 構建操作員列表
    operators = settings[chat_id_str]['operators']
    operator_list = []
    
    for user_id, info in operators.items():
        username = info.get('username', '未知')
        added_time = info.get('added_time', '未知時間')
        operator_list.append(f"@{username} (ID: {user_id})\n添加時間: {added_time}")
    
    # 發送操作員列表
    reply = "📋 當前操作員列表:\n\n" + "\n\n".join(operator_list)
    bot.reply_to(message, reply)
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了操作員列表")

# 處理刪除操作員指令
@bot.message_handler(regexp=r'^刪除操作員\s+(.+)$')
@error_handler
def handle_delete_operators(message):
    """處理刪除操作員的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 解析指令參數
    match = re.match(r'^刪除操作員\s+(.+)$', message.text)
    if not match:
        bot.reply_to(message, "❌ 使用方式: 刪除操作員 @用戶名1 @用戶名2 ...")
        return
    
    operators_text = match.group(1).strip()
    usernames = re.findall(r'@(\w+)', operators_text)
    
    if not usernames:
        bot.reply_to(message, "❌ 未指定任何用戶名。使用方式: 刪除操作員 @用戶名1 @用戶名2 ...")
        return
    
    # 加載當前設定
    settings = load_data(USER_SETTINGS_FILE)
    
    # 獲取群組設定
    chat_id_str = str(message.chat.id)
    
    # 檢查是否有操作員設定
    if chat_id_str not in settings or 'operators' not in settings[chat_id_str] or not settings[chat_id_str]['operators']:
        bot.reply_to(message, "📝 當前沒有設定任何操作員")
        return
    
    # 刪除指定的操作員
    operators = settings[chat_id_str]['operators']
    deleted_users = []
    not_found_users = []
    
    for username in usernames:
        found = False
        for user_id, info in list(operators.items()):
            if info.get('username') == username:
                del operators[user_id]
                deleted_users.append(f"@{username}")
                found = True
                break
        
        if not found:
            not_found_users.append(f"@{username}")
    
    # 保存設定
    save_data(settings, USER_SETTINGS_FILE)
    
    # 構建回覆訊息
    reply = ""
    if deleted_users:
        reply += f"✅ 已刪除以下操作員:\n{', '.join(deleted_users)}\n"
    
    if not_found_users:
        reply += f"❌ 找不到以下操作員:\n{', '.join(not_found_users)}"
    
    bot.reply_to(message, reply.strip())
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 刪除了操作員: {', '.join(deleted_users)}")

# 處理查看用戶權限指令
@bot.message_handler(commands=['info'])
@error_handler
def handle_user_info(message):
    """處理查看用戶權限的指令"""
    # 解析命令參數
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args and not message.reply_to_message:
        bot.reply_to(message, "❌ 使用方式: /info @用戶名 或回覆要查詢的用戶")
        return
    
    # 獲取目標用戶ID
    target_user_id = None
    target_username = None
    
    try:
        # 如果是回覆某人的訊息
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or str(target_user_id)
        # 如果有指定用戶名
        elif command_args:
            username = command_args[0].replace('@', '')
            # 從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == username:
                    target_user_id = member.user.id
                    target_username = username
                    break
    except Exception as e:
        bot.reply_to(message, f"❌ 查找用戶時出錯: {str(e)}")
        return
    
    if not target_user_id:
        bot.reply_to(message, "❌ 找不到指定的用戶")
        return
    
    # 獲取用戶在群組中的權限狀態
    try:
        user_status = "普通成員"
        user_is_admin = False
        user_is_operator = False
        
        # 檢查是否為管理員
        if is_admin(target_user_id, message.chat.id):
            user_status = "管理員"
            user_is_admin = True
        
        # 檢查是否為操作員
        settings = load_data(USER_SETTINGS_FILE)
        chat_id_str = str(message.chat.id)
        if (chat_id_str in settings and 'operators' in settings[chat_id_str] and 
            str(target_user_id) in settings[chat_id_str]['operators']):
            user_status = "操作員" if not user_is_admin else f"{user_status}、操作員"
            user_is_operator = True
        
        # 獲取用戶詳細資訊
        chat_member = bot.get_chat_member(message.chat.id, target_user_id)
        
        # 構建回覆訊息
        reply = f"👤 用戶資訊: {'@' + target_username if target_username else '未知'}\n"
        reply += f"🆔 用戶ID: {target_user_id}\n"
        reply += f"🏷️ 狀態: {user_status}\n"
        
        if hasattr(chat_member, 'status'):
            reply += f"📊 Telegram狀態: {chat_member.status}\n"
        
        # 如果是操作員，顯示添加時間
        if user_is_operator:
            added_time = settings[chat_id_str]['operators'][str(target_user_id)].get('added_time', '未知時間')
            added_by = settings[chat_id_str]['operators'][str(target_user_id)].get('added_by', '未知')
            reply += f"⏱️ 添加為操作員時間: {added_time}\n"
            reply += f"👤 添加者ID: {added_by}\n"
        
        bot.reply_to(message, reply)
        logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了用戶 {target_username or target_user_id} 的權限狀態")
    
    except Exception as e:
        bot.reply_to(message, f"❌ 獲取用戶信息時出錯: {str(e)}")
        logger.error(f"獲取用戶信息出錯: {str(e)}")

# 處理踢出用戶指令
@bot.message_handler(commands=['kick'])
@error_handler
def handle_kick_command(message):
    """處理踢出用戶的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 解析命令參數
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args and not message.reply_to_message:
        bot.reply_to(message, "❌ 使用方式: /kick @用戶名 [原因] 或回覆要踢出的用戶")
        return
    
    # 獲取目標用戶ID
    target_user_id = None
    target_username = None
    
    try:
        # 如果是回覆某人的訊息
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or str(target_user_id)
        # 如果有指定用戶名
        elif command_args:
            username = command_args[0].replace('@', '')
            # 從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == username:
                    target_user_id = member.user.id
                    target_username = username
                    break
            
            # 如果未找到，嘗試使用正則表達式解析數字ID
            if not target_user_id and command_args[0].isdigit():
                target_user_id = int(command_args[0])
                target_username = str(target_user_id)
    except Exception as e:
        bot.reply_to(message, f"❌ 查找用戶時出錯: {str(e)}")
        return
    
    if not target_user_id:
        bot.reply_to(message, "❌ 找不到指定的用戶")
        return
    
    # 解析踢出原因
    reason = "未指定原因"
    if len(command_args) > 1:
        reason = ' '.join(command_args[1:])
    
    # 檢查目標用戶是否為管理員
    if is_admin(target_user_id, message.chat.id):
        bot.reply_to(message, "❌ 無法踢出管理員")
        return
    
    # 執行踢出操作
    try:
        bot.kick_chat_member(message.chat.id, target_user_id)
        bot.unban_chat_member(message.chat.id, target_user_id)  # 立即解除封禁，使用戶可以再次加入
        
        # 發送成功訊息
        bot.reply_to(message, f"✅ 已踢出用戶 {target_username}\n原因: {reason}")
        logger.info(f"管理員 {message.from_user.username or message.from_user.id} 踢出了用戶 {target_username}，原因: {reason}")
    except Exception as e:
        bot.reply_to(message, f"❌ 踢出用戶時出錯: {str(e)}")
        logger.error(f"踢出用戶出錯: {str(e)}")

# 處理查看管理員命令列表
@bot.message_handler(commands=['admin'])
@error_handler
def handle_admin_commands(message):
    """處理查看管理員命令列表的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    admin_commands = """<b>🛠️ 管理員命令列表</b>

<b>👤 成員管理</b>
/kick - 踢出用戶
/ban - 禁言用戶
/unban - 解除禁言

<b>⚠️ 警告系統</b>
/warn - 警告用戶
/unwarn - 移除警告
/warns - 查看用戶警告次數

<b>🧹 清理訊息</b>
/del - 刪除單一訊息

<b>📋 其他</b>
/info - 查看用戶權限
/restart - 重啟機器人
"""
    
    bot.reply_to(message, admin_commands, parse_mode='HTML')
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 查看了管理員命令列表")

# 處理查看管理員名單
@bot.message_handler(func=lambda message: message.text == '📋查看管理員')
@error_handler
def handle_list_admins(message):
    """處理查看群組管理員的請求"""
    try:
        # 獲取群組管理員列表
        admins = bot.get_chat_administrators(message.chat.id)
        
        # 構建管理員列表訊息
        admin_list = []
        for admin in admins:
            status = "👑 群主" if admin.status == "creator" else "👮 管理員"
            username = f"@{admin.user.username}" if admin.user.username else admin.user.first_name
            admin_list.append(f"{status}: {username} (ID: {admin.user.id})")
        
        # 發送管理員列表
        reply = "<b>📋 群組管理員列表</b>\n\n" + "\n".join(admin_list)
        bot.reply_to(message, reply, parse_mode='HTML')
        logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了群組管理員列表")
    
    except Exception as e:
        bot.reply_to(message, f"❌ 獲取管理員列表時出錯: {str(e)}")
        logger.error(f"獲取管理員列表出錯: {str(e)}")

# 警告系統 - 警告用戶
@bot.message_handler(commands=['warn'])
@error_handler
def handle_warn_command(message):
    """處理警告用戶的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 解析命令參數
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args and not message.reply_to_message:
        bot.reply_to(message, "❌ 使用方式: /warn @用戶名 [原因] 或回覆要警告的用戶")
        return
    
    # 獲取目標用戶ID
    target_user_id = None
    target_username = None
    
    try:
        # 如果是回覆某人的訊息
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or str(target_user_id)
        # 如果有指定用戶名
        elif command_args:
            username = command_args[0].replace('@', '')
            # 從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == username:
                    target_user_id = member.user.id
                    target_username = username
                    break
            
            # 如果未找到，嘗試使用正則表達式解析數字ID
            if not target_user_id and command_args[0].isdigit():
                target_user_id = int(command_args[0])
                target_username = str(target_user_id)
    except Exception as e:
        bot.reply_to(message, f"❌ 查找用戶時出錯: {str(e)}")
        return
    
    if not target_user_id:
        bot.reply_to(message, "❌ 找不到指定的用戶")
        return
    
    # 解析警告原因
    reason = "未指定原因"
    if len(command_args) > 1:
        reason = ' '.join(command_args[1:])
    
    # 檢查目標用戶是否為管理員
    if is_admin(target_user_id, message.chat.id):
        bot.reply_to(message, "❌ 無法警告管理員")
        return
    
    # 加載警告系統設定
    settings = load_data(USER_SETTINGS_FILE)
    chat_id_str = str(message.chat.id)
    
    # 初始化群組警告系統設定
    if chat_id_str not in settings:
        settings[chat_id_str] = {}
    if 'warnings' not in settings[chat_id_str]:
        settings[chat_id_str]['warnings'] = {}
    
    # 獲取或初始化用戶警告數
    user_id_str = str(target_user_id)
    if user_id_str not in settings[chat_id_str]['warnings']:
        settings[chat_id_str]['warnings'][user_id_str] = {
            'count': 0,
            'reasons': [],
            'warned_by': [],
            'timestamps': []
        }
    
    # 增加警告次數
    settings[chat_id_str]['warnings'][user_id_str]['count'] += 1
    settings[chat_id_str]['warnings'][user_id_str]['reasons'].append(reason)
    settings[chat_id_str]['warnings'][user_id_str]['warned_by'].append(message.from_user.id)
    settings[chat_id_str]['warnings'][user_id_str]['timestamps'].append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 獲取當前警告次數
    warn_count = settings[chat_id_str]['warnings'][user_id_str]['count']
    
    # 檢查是否達到禁言閾值
    if warn_count >= 3:
        try:
            # 設置24小時禁言
            until_date = int((datetime.now() + timedelta(hours=24)).timestamp())
            
            bot.restrict_chat_member(
                message.chat.id, 
                target_user_id,
                permissions=telebot.types.ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False
                ),
                until_date=until_date
            )
            
            # 重置警告次數
            settings[chat_id_str]['warnings'][user_id_str]['count'] = 0
            settings[chat_id_str]['warnings'][user_id_str]['banned_history'] = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'banned_by': message.from_user.id,
                'reason': f"達到警告上限 ({warn_count}次)"
            }
            
            # 發送禁言通知
            bot.reply_to(message, f"⚠️ 用戶 {target_username} 已收到第 {warn_count} 次警告，已自動禁言24小時。\n原因: {reason}")
        except Exception as e:
            bot.reply_to(message, f"⚠️ 用戶已收到第 {warn_count} 次警告，但禁言失敗: {str(e)}")
    else:
        # 發送警告通知
        bot.reply_to(message, f"⚠️ 已警告用戶 {target_username} ({warn_count}/3)\n原因: {reason}")
    
    # 保存設定
    save_data(settings, USER_SETTINGS_FILE)
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 警告了用戶 {target_username}，原因: {reason}，當前警告: {warn_count}/3")

# 警告系統 - 移除警告
@bot.message_handler(commands=['unwarn'])
@error_handler
def handle_unwarn_command(message):
    """處理移除用戶警告的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 解析命令參數
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args and not message.reply_to_message:
        bot.reply_to(message, "❌ 使用方式: /unwarn @用戶名 或回覆要移除警告的用戶")
        return
    
    # 獲取目標用戶ID
    target_user_id = None
    target_username = None
    
    try:
        # 如果是回覆某人的訊息
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or str(target_user_id)
        # 如果有指定用戶名
        elif command_args:
            username = command_args[0].replace('@', '')
            # 從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == username:
                    target_user_id = member.user.id
                    target_username = username
                    break
            
            # 如果未找到，嘗試使用正則表達式解析數字ID
            if not target_user_id and command_args[0].isdigit():
                target_user_id = int(command_args[0])
                target_username = str(target_user_id)
    except Exception as e:
        bot.reply_to(message, f"❌ 查找用戶時出錯: {str(e)}")
        return
    
    if not target_user_id:
        bot.reply_to(message, "❌ 找不到指定的用戶")
        return
    
    # 加載警告系統設定
    settings = load_data(USER_SETTINGS_FILE)
    chat_id_str = str(message.chat.id)
    
    # 檢查是否有警告記錄
    if (chat_id_str not in settings or 
        'warnings' not in settings[chat_id_str] or 
        str(target_user_id) not in settings[chat_id_str]['warnings'] or
        settings[chat_id_str]['warnings'][str(target_user_id)]['count'] <= 0):
        bot.reply_to(message, f"⚠️ 用戶 {target_username} 目前沒有警告記錄")
        return
    
    # 減少警告次數
    user_id_str = str(target_user_id)
    settings[chat_id_str]['warnings'][user_id_str]['count'] -= 1
    warn_count = settings[chat_id_str]['warnings'][user_id_str]['count']
    
    # 如果有警告記錄，移除最後一條
    if len(settings[chat_id_str]['warnings'][user_id_str]['reasons']) > 0:
        settings[chat_id_str]['warnings'][user_id_str]['reasons'].pop()
    if len(settings[chat_id_str]['warnings'][user_id_str]['warned_by']) > 0:
        settings[chat_id_str]['warnings'][user_id_str]['warned_by'].pop()
    if len(settings[chat_id_str]['warnings'][user_id_str]['timestamps']) > 0:
        settings[chat_id_str]['warnings'][user_id_str]['timestamps'].pop()
    
    # 保存設定
    save_data(settings, USER_SETTINGS_FILE)
    
    # 發送通知
    bot.reply_to(message, f"✅ 已移除用戶 {target_username} 的一次警告，當前警告次數: {warn_count}/3")
    logger.info(f"管理員 {message.from_user.username or message.from_user.id} 移除了用戶 {target_username} 的一次警告，當前警告: {warn_count}/3")

# 警告系統 - 查看警告
@bot.message_handler(commands=['warns'])
@error_handler
def handle_warns_command(message):
    """處理查看用戶警告次數的指令"""
    # 解析命令參數
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args and not message.reply_to_message:
        bot.reply_to(message, "❌ 使用方式: /warns @用戶名 或回覆要查看警告的用戶")
        return
    
    # 獲取目標用戶ID
    target_user_id = None
    target_username = None
    
    try:
        # 如果是回覆某人的訊息
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or str(target_user_id)
        # 如果有指定用戶名
        elif command_args:
            username = command_args[0].replace('@', '')
            # 從群組成員中尋找
            chat_members = bot.get_chat_administrators(message.chat.id)
            for member in chat_members:
                if member.user.username == username:
                    target_user_id = member.user.id
                    target_username = username
                    break
            
            # 如果未找到，嘗試使用正則表達式解析數字ID
            if not target_user_id and command_args[0].isdigit():
                target_user_id = int(command_args[0])
                target_username = str(target_user_id)
    except Exception as e:
        bot.reply_to(message, f"❌ 查找用戶時出錯: {str(e)}")
        return
    
    if not target_user_id:
        bot.reply_to(message, "❌ 找不到指定的用戶")
        return
    
    # 加載警告系統設定
    settings = load_data(USER_SETTINGS_FILE)
    chat_id_str = str(message.chat.id)
    
    # 檢查是否有警告記錄
    if (chat_id_str not in settings or 
        'warnings' not in settings[chat_id_str] or 
        str(target_user_id) not in settings[chat_id_str]['warnings']):
        bot.reply_to(message, f"⚠️ 用戶 {target_username} 目前沒有警告記錄")
        return
    
    # 獲取警告記錄
    user_id_str = str(target_user_id)
    warn_data = settings[chat_id_str]['warnings'][user_id_str]
    warn_count = warn_data.get('count', 0)
    reasons = warn_data.get('reasons', [])
    timestamps = warn_data.get('timestamps', [])
    
    # 構建回覆訊息
    reply = f"⚠️ 用戶 {target_username} 的警告記錄: {warn_count}/3\n\n"
    
    if warn_count > 0 and len(reasons) > 0:
        for i in range(min(warn_count, len(reasons))):
            timestamp = timestamps[i] if i < len(timestamps) else "未知時間"
            reason = reasons[i]
            reply += f"{i+1}. [{timestamp}] 原因: {reason}\n"
    
    # 檢查是否有禁言歷史
    if 'banned_history' in warn_data:
        ban_info = warn_data['banned_history']
        reply += f"\n上次禁言時間: {ban_info.get('time', '未知')}\n"
        reply += f"原因: {ban_info.get('reason', '未知')}"
    
    bot.reply_to(message, reply)
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了用戶 {target_username} 的警告記錄")

# 處理 "日期 TW+金額" 格式的訊息
@bot.message_handler(regexp=r'^\s*([0-9/\-\.]+)\s+TW\+\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_date_tw_add(message):
    """處理特定日期台幣收入記帳"""
    match = re.match(r'^\s*([0-9/\-\.]+)\s+TW\+\s*(\d+(\.\d+)?)\s*$', message.text)
    date_str = match.group(1)
    amount = float(match.group(2))
    
    date = parse_date(date_str)
    
    add_transaction(message.from_user.id, date, 'TW', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄 {date_display} 的台幣收入：NT${amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了 {date_display} 的台幣收入 {amount}")

# 處理 "日期 TW-金額" 格式的訊息
@bot.message_handler(regexp=r'^\s*([0-9/\-\.]+)\s+TW\-\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_date_tw_subtract(message):
    """處理特定日期台幣支出記帳"""
    match = re.match(r'^\s*([0-9/\-\.]+)\s+TW\-\s*(\d+(\.\d+)?)\s*$', message.text)
    date_str = match.group(1)
    amount = -float(match.group(2))
    
    date = parse_date(date_str)
    
    add_transaction(message.from_user.id, date, 'TW', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄 {date_display} 的台幣支出：NT${-amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了 {date_display} 的台幣支出 {-amount}")

# 處理 "日期 CN+金額" 格式的訊息
@bot.message_handler(regexp=r'^\s*([0-9/\-\.]+)\s+CN\+\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_date_cn_add(message):
    """處理特定日期人民幣收入記帳"""
    match = re.match(r'^\s*([0-9/\-\.]+)\s+CN\+\s*(\d+(\.\d+)?)\s*$', message.text)
    date_str = match.group(1)
    amount = float(match.group(2))
    
    date = parse_date(date_str)
    
    add_transaction(message.from_user.id, date, 'CN', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄 {date_display} 的人民幣收入：CN¥{amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了 {date_display} 的人民幣收入 {amount}")

# 處理 "日期 CN-金額" 格式的訊息
@bot.message_handler(regexp=r'^\s*([0-9/\-\.]+)\s+CN\-\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_date_cn_subtract(message):
    """處理特定日期人民幣支出記帳"""
    match = re.match(r'^\s*([0-9/\-\.]+)\s+CN\-\s*(\d+(\.\d+)?)\s*$', message.text)
    date_str = match.group(1)
    amount = -float(match.group(2))
    
    date = parse_date(date_str)
    
    add_transaction(message.from_user.id, date, 'CN', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄 {date_display} 的人民幣支出：CN¥{-amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了 {date_display} 的人民幣支出 {-amount}")

# 處理直接輸入的 "TW+金額" 格式
@bot.message_handler(regexp=r'^\s*TW\+\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_direct_tw_add(message):
    """處理直接輸入的台幣收入記帳"""
    match = re.match(r'^\s*TW\+\s*(\d+(\.\d+)?)\s*$', message.text)
    amount = float(match.group(1))
    
    # 使用當前日期
    date = datetime.now().strftime('%Y-%m-%d')
    
    add_transaction(message.from_user.id, date, 'TW', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄今日({date_display})的台幣收入：NT${amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了今日的台幣收入 {amount}")

# 處理直接輸入的 "TW-金額" 格式
@bot.message_handler(regexp=r'^\s*TW\-\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_direct_tw_subtract(message):
    """處理直接輸入的台幣支出記帳"""
    match = re.match(r'^\s*TW\-\s*(\d+(\.\d+)?)\s*$', message.text)
    amount = -float(match.group(1))
    
    # 使用當前日期
    date = datetime.now().strftime('%Y-%m-%d')
    
    add_transaction(message.from_user.id, date, 'TW', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄今日({date_display})的台幣支出：NT${-amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了今日的台幣支出 {-amount}")

# 處理直接輸入的 "CN+金額" 格式
@bot.message_handler(regexp=r'^\s*CN\+\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_direct_cn_add(message):
    """處理直接輸入的人民幣收入記帳"""
    match = re.match(r'^\s*CN\+\s*(\d+(\.\d+)?)\s*$', message.text)
    amount = float(match.group(1))
    
    # 使用當前日期
    date = datetime.now().strftime('%Y-%m-%d')
    
    add_transaction(message.from_user.id, date, 'CN', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄今日({date_display})的人民幣收入：CN¥{amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了今日的人民幣收入 {amount}")

# 處理直接輸入的 "CN-金額" 格式
@bot.message_handler(regexp=r'^\s*CN\-\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_direct_cn_subtract(message):
    """處理直接輸入的人民幣支出記帳"""
    match = re.match(r'^\s*CN\-\s*(\d+(\.\d+)?)\s*$', message.text)
    amount = -float(match.group(1))
    
    # 使用當前日期
    date = datetime.now().strftime('%Y-%m-%d')
    
    add_transaction(message.from_user.id, date, 'CN', amount)
    
    date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
    bot.reply_to(message, f"✅ 已記錄今日({date_display})的人民幣支出：CN¥{-amount:,.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了今日的人民幣支出 {-amount}")

# 移除既有的處理函數
# 處理直接輸入的記帳格式 - 同時處理多種格式
@bot.message_handler(func=lambda message: re.match(r'^\s*(?:TW|CN)[+\-]\s*\d+(?:\.\d+)?\s*$', message.text) or 
                                         re.match(r'^\s*(?:[0-9/\-\.]+)\s+(?:TW|CN)[+\-]\s*\d+(?:\.\d+)?\s*$', message.text),
                     content_types=['text'])
@error_handler
def handle_accounting_input(message):
    """通用記帳處理函數，支持多種格式
    
    這個函數處理直接在聊天中輸入的記帳指令，不需要透過按鈕點擊。
    支持格式：
    1. 日期 TW+金額 (如 5/01 TW+350000)
    2. 日期 TW-金額 (如 5/01 TW-100)
    3. 日期 CN+金額 (如 5/01 CN+350000)
    4. 日期 CN-金額 (如 5/01 CN-100)
    5. TW+金額 (如 TW+1000)
    6. TW-金額 (如 TW-100)
    7. CN+金額 (如 CN+1000)
    8. CN-金額 (如 CN-100)
    
    注意：此功能與按鈕功能並行，用戶可以直接輸入或使用按鈕回覆。
    """
    text = message.text.strip()
    
    # 檢查是否為帶日期的格式（如 5/01 TW+350000）
    date_match = re.match(r'^\s*([0-9/\-\.]+)\s+(TW|CN)([+\-])\s*(\d+(?:\.\d+)?)\s*$', text)
    if date_match:
        date_str = date_match.group(1)
        currency = date_match.group(2)
        op = date_match.group(3)
        amount = float(date_match.group(4))
        
        # 轉換日期格式
        date = parse_date(date_str)
        date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
        
        # 設置金額
        if op == '-':
            amount = -amount
        
        # 記錄交易
        add_transaction(message.from_user.id, date, currency, amount)
        
        # 回覆確認訊息
        if currency == 'TW':
            currency_symbol = 'NT$'
            if amount > 0:
                reply = f"✅ 已記錄 {date_display} 的台幣收入：{currency_symbol}{abs(amount):,.0f}"
            else:
                reply = f"✅ 已記錄 {date_display} 的台幣支出：{currency_symbol}{abs(amount):,.0f}"
        else:  # CN
            currency_symbol = 'CN¥'
            if amount > 0:
                reply = f"✅ 已記錄 {date_display} 的人民幣收入：{currency_symbol}{abs(amount):,.0f}"
            else:
                reply = f"✅ 已記錄 {date_display} 的人民幣支出：{currency_symbol}{abs(amount):,.0f}"
        
        bot.reply_to(message, reply)
        logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了 {date_display} 的 {currency} {'收入' if amount > 0 else '支出'} {abs(amount)}")
        return
    
    # 處理不帶日期的格式（如 TW+1000）
    direct_match = re.match(r'^\s*(TW|CN)([+\-])\s*(\d+(?:\.\d+)?)\s*$', text)
    if direct_match:
        currency = direct_match.group(1)
        op = direct_match.group(2)
        amount = float(direct_match.group(3))
        
        # 使用當前日期
        date = datetime.now().strftime('%Y-%m-%d')
        date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d')
        
        # 設置金額
        if op == '-':
            amount = -amount
        
        # 記錄交易
        add_transaction(message.from_user.id, date, currency, amount)
        
        # 回覆確認訊息
        if currency == 'TW':
            currency_symbol = 'NT$'
            if amount > 0:
                reply = f"✅ 已記錄今日({date_display})的台幣收入：{currency_symbol}{abs(amount):,.0f}"
            else:
                reply = f"✅ 已記錄今日({date_display})的台幣支出：{currency_symbol}{abs(amount):,.0f}"
        else:  # CN
            currency_symbol = 'CN¥'
            if amount > 0:
                reply = f"✅ 已記錄今日({date_display})的人民幣收入：{currency_symbol}{abs(amount):,.0f}"
            else:
                reply = f"✅ 已記錄今日({date_display})的人民幣支出：{currency_symbol}{abs(amount):,.0f}"
        
        bot.reply_to(message, reply)
        logger.info(f"用戶 {message.from_user.username or message.from_user.id} 記錄了今日的 {currency} {'收入' if amount > 0 else '支出'} {abs(amount)}")
        return

# 處理公桶資金管理命令
@bot.message_handler(regexp=r'^\s*公桶([+\-])\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_public_fund(message):
    """處理公桶資金增減指令"""
    # 檢查用戶是否為管理員或操作員
    if not is_admin(message.from_user.id, message.chat.id, check_operator=True):
        bot.reply_to(message, "❌ 此功能僅限管理員或操作員使用")
        return
        
    match = re.match(r'^\s*公桶([+\-])\s*(\d+(\.\d+)?)\s*$', message.text)
    op = match.group(1)
    amount = float(match.group(2))
    
    # 設置金額
    if op == '-':
        amount = -amount
    
    # 更新資金
    update_fund("public", amount)
    
    # 回覆確認訊息
    if amount > 0:
        reply = f"✅ 已添加公桶資金：USDT${amount:.2f}"
    else:
        reply = f"✅ 已從公桶資金中扣除：USDT${-amount:.2f}"
    
    bot.reply_to(message, reply)
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} {'增加' if amount > 0 else '減少'}了公桶資金 {abs(amount)}")

# 處理私人資金管理命令
@bot.message_handler(regexp=r'^\s*私人([+\-])\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_private_fund(message):
    """處理私人資金增減指令"""
    # 檢查用戶是否為管理員或操作員
    if not is_admin(message.from_user.id, message.chat.id, check_operator=True):
        bot.reply_to(message, "❌ 此功能僅限管理員或操作員使用")
        return
        
    match = re.match(r'^\s*私人([+\-])\s*(\d+(\.\d+)?)\s*$', message.text)
    op = match.group(1)
    amount = float(match.group(2))
    
    # 設置金額
    if op == '-':
        amount = -amount
    
    # 更新資金
    update_fund("private", amount)
    
    # 回覆確認訊息
    if amount > 0:
        reply = f"✅ 已添加私人資金：USDT${amount:.2f}"
    else:
        reply = f"✅ 已從私人資金中扣除：USDT${-amount:.2f}"
    
    bot.reply_to(message, reply)
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} {'增加' if amount > 0 else '減少'}了私人資金 {abs(amount)}")

# 生成綜合報表 (所有用戶資料總和)

# 此函數已移至文件前面
# 特殊用戶資金設定
def set_special_user_funds(fund_type, amount):
    """設置特殊用戶的公桶或私人資金"""
    settings = load_data(USER_SETTINGS_FILE)
    if SPECIAL_USER_NAME not in settings:
        settings[SPECIAL_USER_NAME] = {}
    
    settings[SPECIAL_USER_NAME][fund_type] = float(amount)
    save_data(settings, USER_SETTINGS_FILE)

# 獲取特殊用戶資金
def get_special_user_funds(fund_type):
    """獲取特殊用戶的公桶或私人資金"""
    settings = load_data(USER_SETTINGS_FILE)
    return settings.get(SPECIAL_USER_NAME, {}).get(fund_type, 0)

# 特殊用戶公桶資金處理
@bot.message_handler(regexp=r'^\s*總表公桶\s*=\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_special_public_fund(message):
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 僅限管理員使用此命令")
        return

    match = re.match(r'^\s*總表公桶\s*=\s*(\d+(\.\d+)?)\s*$', message.text)
    amount = float(match.group(1))
    
    set_special_user_funds('public_funds', amount)
    
    bot.reply_to(message, f"✅ 已設置總表公桶資金為：USDT${amount:.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 設置了總表公桶資金為 {amount}")

# 特殊用戶私人資金處理
@bot.message_handler(regexp=r'^\s*總表私人\s*=\s*(\d+(\.\d+)?)\s*$')
@error_handler
def handle_special_private_fund(message):
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 僅限管理員使用此命令")
        return

    match = re.match(r'^\s*總表私人\s*=\s*(\d+(\.\d+)?)\s*$', message.text)
    amount = float(match.group(1))
    
    set_special_user_funds('private_funds', amount)
    
    bot.reply_to(message, f"✅ 已設置總表私人資金為：USDT${amount:.0f}")
    logger.info(f"用戶 {message.from_user.username or message.from_user.id} 設置了總表私人資金為 {amount}")

# 查看特殊用戶綜合報表
@bot.message_handler(func=lambda message: message.text == '總表')
@error_handler
def handle_special_user_report(message):
    """處理總表指令 - 查看所有用戶合計報表"""
    try:
        logger.info(f"[已棄用] 正在處理'總表'指令，來自用戶 {message.from_user.username or message.from_user.id}")
        # 轉發到高優先級處理器
        handle_total_report_commands_highest_priority(message)
    except Exception as e:
        bot.reply_to(message, f"❌ 生成總表時發生錯誤：{str(e)}")
        logger.error(f"生成總表錯誤：{str(e)}")
        logger.error(traceback.format_exc())  # 添加詳細的錯誤追蹤

@bot.message_handler(regexp=r'^總表\s+(\d{4})-(\d{1,2})$')
@error_handler
def handle_special_user_history_report(message):
    """處理歷史總表指令 - 查看特定月份的合計報表"""
    try:
        logger.info(f"正在處理'總表 YYYY-MM'指令，來自用戶 {message.from_user.username or message.from_user.id}")
        match = re.match(r'^總表\s+(\d{4})-(\d{1,2})$', message.text)
        year = int(match.group(1))
        month = int(match.group(2))
        
        report = generate_combined_report(month, year)
        bot.reply_to(message, report, parse_mode='HTML')
        logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了 {year}-{month} 總表")
    except Exception as e:
        bot.reply_to(message, f"❌ 生成歷史總表時發生錯誤：{str(e)}")
        logger.error(f"生成歷史總表錯誤：{str(e)}")
        logger.error(traceback.format_exc())  # 添加詳細的錯誤追蹤

@bot.message_handler(func=lambda message: message.text.strip() == '總表資金', content_types=['text'])
@error_handler
def handle_special_user_funds(message):
    """處理總表資金指令 - 查看總表資金狀態"""
    try:
        logger.info(f"[已棄用] 正在處理'總表資金'指令，來自用戶 {message.from_user.username or message.from_user.id}")
        # 轉發到高優先級處理器
        handle_total_report_commands_highest_priority(message)
    except Exception as e:
        bot.reply_to(message, f"❌ 獲取總表資金狀態時發生錯誤：{str(e)}")
        logger.error(f"獲取總表資金狀態錯誤：{str(e)}")
        logger.error(traceback.format_exc())  # 添加詳細的錯誤追蹤

# 優先處理總表相關指令 - 高優先級處理器
@bot.message_handler(func=lambda message: message.text and message.text.strip() in ['總表', '總表資金'] or 
                                         (message.text and re.match(r'^總表\s+\d{4}-\d{1,2}$', message.text.strip())), 
                     content_types=['text'])
@error_handler
def handle_all_total_report_commands_priority(message):
    """高優先級處理器 - 總表相關所有指令"""
    text = message.text.strip()
    logger.info(f"高優先級處理器捕獲到總表相關指令: '{text}'，來自用戶 {message.from_user.username or message.from_user.id}")
    
    try:
        if text == '總表':
            # 處理總表指令
            report = generate_combined_report()
            bot.reply_to(message, report, parse_mode='HTML')
            logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了總表")
            
        elif text == '總表資金':
            # 處理總表資金指令
            public_funds = get_special_user_funds('public_funds')
            private_funds = get_special_user_funds('private_funds')
            
            funds_info = (
                f"<b>【M8P總表資金狀態】</b>\n"
                f"公桶: <code>USDT${public_funds:.0f}</code>\n"
                f"私人: <code>USDT${private_funds:.0f}</code>"
            )
            
            bot.reply_to(message, funds_info, parse_mode='HTML')
            logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了總表資金狀態")
            
        elif re.match(r'^總表\s+\d{4}-\d{1,2}$', text):
            # 處理歷史總表指令
            match = re.match(r'^總表\s+(\d{4})-(\d{1,2})$', text)
            year = int(match.group(1))
            month = int(match.group(2))
            
            report = generate_combined_report(month, year)
            bot.reply_to(message, report, parse_mode='HTML')
            logger.info(f"用戶 {message.from_user.username or message.from_user.id} 查看了 {year}-{month} 總表")
    except Exception as e:
        bot.reply_to(message, f"❌ 處理總表指令時發生錯誤：{str(e)}")
        logger.error(f"處理總表指令錯誤：{str(e)}")
        logger.error(traceback.format_exc())  # 添加詳細的錯誤追蹤

# 處理歡迎詞設定
@bot.message_handler(regexp=r'^設定歡迎詞：(.+)$')
@error_handler
def handle_set_welcome_text(message):
    """處理設定歡迎詞的指令"""
    # 檢查是否為管理員
    if not is_admin(message.from_user.id, message.chat.id):
        bot.reply_to(message, "❌ 此功能僅限群組管理員使用")
        return
    
    # 獲取歡迎詞內容
    match = re.match(r'^設定歡迎詞：(.+)$', message.text)
    welcome_message = match.group(1).strip()
    
    try:
        # 保存歡迎詞設定
        settings = load_data(USER_SETTINGS_FILE)
        
        # 使用聊天ID作為鍵，以便群組特定設定
        chat_id_str = str(message.chat.id)
        if chat_id_str not in settings:
            settings[chat_id_str] = {}
        
        settings[chat_id_str]['welcome_message'] = welcome_message
        save_data(settings, USER_SETTINGS_FILE)
        
        # 回覆成功訊息
        bot.reply_to(message, f"✅ 歡迎詞已成功設定為：\n\n<pre>{welcome_message}</pre>", parse_mode='HTML')
        logger.info(f"管理員 {message.from_user.username or message.from_user.id} 設定了新的歡迎詞")
    except Exception as e:
        bot.reply_to(message, f"❌ 設定歡迎詞時出錯：{str(e)}")
        logger.error(f"設定歡迎詞出錯: {str(e)}")