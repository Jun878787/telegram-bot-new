import json
from datetime import datetime
import os

class Accounting:
    def __init__(self, data_file='accounting_data.json'):
        self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {'records': []}
        return {'records': []}

    def _save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_record(self, amount, category, description, date=None):
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        record = {
            'id': len(self.data['records']) + 1,
            'date': date,
            'amount': float(amount),
            'category': category,
            'description': description
        }
        
        self.data['records'].append(record)
        self._save_data()
        return record

    def get_records(self, start_date=None, end_date=None, category=None):
        records = self.data['records']
        
        if start_date:
            records = [r for r in records if r['date'] >= start_date]
        if end_date:
            records = [r for r in records if r['date'] <= end_date]
        if category:
            records = [r for r in records if r['category'] == category]
            
        return records

    def delete_record(self, record_id):
        for i, record in enumerate(self.data['records']):
            if record['id'] == record_id:
                del self.data['records'][i]
                self._save_data()
                return True
        return False

    def get_summary(self, category=None):
        records = self.get_records(category=category)
        total = sum(record['amount'] for record in records)
        return {
            'total': total,
            'count': len(records),
            'category': category or '全部'
        }

    def get_categories(self):
        return sorted(list(set(r['category'] for r in self.data['records']))) 