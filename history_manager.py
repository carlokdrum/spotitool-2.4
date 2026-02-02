import json
import os

class HistoryManager:
    def __init__(self, filename='history.json'):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                json.dump([], f)

    def get_history(self):
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except:
            return []

    def add_entry(self, name, url, count):
        from datetime import datetime
        history = self.get_history()
        history.insert(0, {
            'name': name,
            'playlist_url': url,
            'total_added': count,
            'date': datetime.now().strftime("%Y-%m-%d")
        })
        with open(self.filename, 'w') as f:
            json.dump(history[:50], f)

    def update_entry(self, url, name=None, count=None):
        history = self.get_history()
        updated = False
        for entry in history:
            if entry.get('playlist_url') == url:
                if name: entry['name'] = name
                if count is not None: entry['total_added'] = count
                updated = True
        if updated:
            with open(self.filename, 'w') as f:
                json.dump(history, f)

    def remove_entry(self, url):
        history = self.get_history()
        history = [e for e in history if e.get('playlist_url') != url]
        with open(self.filename, 'w') as f:
            json.dump(history, f)
