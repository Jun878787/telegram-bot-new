import json
import os
from datetime import datetime

class Config:
    def __init__(self):
        self.config_file = 'config.json'
        self.data = {
            'deposits': [],
            'withdrawals': [],
            'operators': [],
            'rates': {
                'deposit': 33.25,
                'withdrawal': 33.25
            },
            'warnings': {},  # 用戶警告次數
            'broadcast_mode': False,
            'welcome_message': '👋 歡迎 {SURNAME} Go to 北金 North™Sea ᴍ8ᴘ👋',  # 預設歡迎詞
            'welcome_message_enabled': True,
            'farewell_message': '👋 {SURNAME} 已離開群組，期待再相會！',
            'farewell_message_enabled': True,
            'scheduled_messages': [],
            'scheduled_message_enabled': True
        }
        self.load_data()

    def load_data(self):
        """載入配置文件"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                # 更新現有數據，保留預設值
                self.data.update(loaded_data)
        self.save_data()

    def save_data(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_transaction(self, amount, type_):
        """添加交易記錄"""
        transaction = {
            'time': datetime.now().strftime('%H:%M'),
            'amount': amount if type_ == 'deposit' else -abs(amount)
        }
        
        if type_ == 'deposit':
            self.data['deposits'].append(transaction)
        else:
            self.data['withdrawals'].append(transaction)
        
        self.save_data()
        return True

    def cancel_last_deposit(self):
        """撤銷最後一筆入款"""
        if self.data['deposits']:
            self.data['deposits'].pop()
            self.save_data()
            return True
        return False

    def cancel_last_withdrawal(self):
        """撤銷最後一筆出款"""
        if self.data['withdrawals']:
            self.data['withdrawals'].pop()
            self.save_data()
            return True
        return False

    def get_transaction_summary(self):
        """獲取交易摘要"""
        total_deposit = sum(t['amount'] for t in self.data['deposits'])
        processed_amount = sum(t['amount'] for t in self.data['withdrawals'])
        
        return {
            'deposits': self.data['deposits'],
            'withdrawals': self.data['withdrawals'],
            'deposit_count': len(self.data['deposits']),
            'withdrawal_count': len(self.data['withdrawals']),
            'total_deposit': total_deposit,
            'processed_amount': abs(processed_amount)
        }

    def get_rates(self):
        """獲取匯率"""
        return self.data['rates']

    def set_deposit_rate(self, rate):
        """設定入款匯率"""
        self.data['rates']['deposit'] = float(rate)
        self.save_data()

    def set_withdrawal_rate(self, rate):
        """設定出款匯率"""
        self.data['rates']['withdrawal'] = float(rate)
        self.save_data()

    def set_broadcast_mode(self, enabled):
        """設定群發廣播模式"""
        self.data['broadcast_mode'] = enabled
        self.save_data()

    def is_broadcast_mode(self):
        """檢查是否為群發廣播模式"""
        return self.data.get('broadcast_mode', False)

    def is_operator(self, user_id):
        """檢查用戶是否為操作員"""
        return str(user_id) in self.data['operators']

    def add_operator(self, user_id):
        """添加操作員"""
        if str(user_id) not in self.data['operators']:
            self.data['operators'].append(str(user_id))
            self.save_data()
            return True
        return False

    def remove_operator(self, user_id):
        """移除操作員"""
        if str(user_id) in self.data['operators']:
            self.data['operators'].remove(str(user_id))
            self.save_data()
            return True
        return False

    def get_operators(self):
        """獲取所有操作員"""
        return self.data['operators']

    def clear_today_transactions(self):
        """清空今日交易記錄"""
        self.data['deposits'] = []
        self.data['withdrawals'] = []
        self.save_data()

    def clear_all_transactions(self):
        """清空所有交易記錄"""
        self.clear_today_transactions()

    def add_warning(self, user_id):
        """添加警告"""
        user_id = str(user_id)
        if user_id not in self.data['warnings']:
            self.data['warnings'][user_id] = 0
        self.data['warnings'][user_id] += 1
        self.save_data()
        return self.data['warnings'][user_id]

    def remove_warning(self, user_id):
        """移除警告"""
        user_id = str(user_id)
        if user_id in self.data['warnings'] and self.data['warnings'][user_id] > 0:
            self.data['warnings'][user_id] -= 1
            self.save_data()
        return self.get_warnings(user_id)

    def get_warnings(self, user_id):
        """獲取警告次數"""
        user_id = str(user_id)
        return self.data['warnings'].get(user_id, 0)

    def clear_warnings(self, user_id):
        """清空警告次數"""
        user_id = str(user_id)
        if user_id in self.data['warnings']:
            self.data['warnings'][user_id] = 0
            self.save_data()

    def get_welcome_message(self):
        """獲取歡迎訊息"""
        return self.data.get('welcome_message', '👋 歡迎 {SURNAME} Go to 北金 North™Sea ᴍ8ᴘ👋')

    def set_welcome_message(self, message):
        """設置歡迎訊息"""
        self.data['welcome_message'] = message
        self.save_data()

    def get_welcome_message_status(self):
        """獲取歡迎訊息狀態"""
        return self.data.get('welcome_message_enabled', True)

    def set_welcome_message_status(self, status):
        """設置歡迎訊息狀態"""
        self.data['welcome_message_enabled'] = status
        self.save_data()

    def clear_welcome_message(self):
        """清除歡迎訊息"""
        self.data['welcome_message'] = '👋 歡迎 {SURNAME} Go to 北金 North™Sea ᴍ8ᴘ👋'
        self.save_data()

    def get_farewell_message(self):
        """獲取告別訊息"""
        return self.data.get('farewell_message', '👋 {SURNAME} 已離開群組，期待再相會！')

    def set_farewell_message(self, message):
        """設置告別訊息"""
        self.data['farewell_message'] = message
        self.save_data()

    def get_farewell_message_status(self):
        """獲取告別訊息狀態"""
        return self.data.get('farewell_message_enabled', True)

    def set_farewell_message_status(self, status):
        """設置告別訊息狀態"""
        self.data['farewell_message_enabled'] = status
        self.save_data()

    def clear_farewell_message(self):
        """清除告別訊息"""
        self.data['farewell_message'] = '👋 {SURNAME} 已離開群組，期待再相會！'
        self.save_data()

    def get_scheduled_message_status(self):
        """獲取排程訊息狀態"""
        return self.data.get('scheduled_message_enabled', True)

    def set_scheduled_message_status(self, status):
        """設置排程訊息狀態"""
        self.data['scheduled_message_enabled'] = status
        self.save_data()

    def add_scheduled_message(self, time, content):
        """添加排程訊息"""
        if 'scheduled_messages' not in self.data:
            self.data['scheduled_messages'] = []
        
        # 限制最多3個排程訊息
        if len(self.data['scheduled_messages']) >= 3:
            self.data['scheduled_messages'].pop(0)
        
        self.data['scheduled_messages'].append({
            'time': time,
            'content': content
        })
        self.save_data()

    def get_scheduled_message(self, index):
        """獲取指定排程訊息"""
        if 'scheduled_messages' not in self.data:
            return None
        
        try:
            return self.data['scheduled_messages'][index-1]
        except IndexError:
            return None

    def clear_scheduled_messages(self):
        """清除所有排程訊息"""
        self.data['scheduled_messages'] = []
        self.save_data() 