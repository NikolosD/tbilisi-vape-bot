#!/usr/bin/env python3
"""
Разработческий сервер с автоматической перезагрузкой
"""
import sys
import subprocess
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class BotReloader(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.restart_bot()
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Перезагружаем только при изменении Python файлов
        if event.src_path.endswith('.py'):
            print(f"🔄 Файл изменен: {event.src_path}")
            self.restart_bot()
    
    def restart_bot(self):
        if self.process:
            print("🛑 Останавливаем бот...")
            self.process.terminate()
            self.process.wait()
        
        print("🚀 Запускаем бот...")
        self.process = subprocess.Popen([sys.executable, "main.py"])

if __name__ == "__main__":
    # Следим за изменениями в текущей директории
    event_handler = BotReloader()
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()
    
    print("👀 Отслеживание изменений запущено...")
    print("💡 Нажмите Ctrl+C для остановки")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Останавливаем...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    
    observer.join()