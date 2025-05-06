#!/usr/bin/env python3
import os
import sys
import subprocess
import importlib.util

def check_module(module_name):
    """檢查模組是否已安裝"""
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        print(f"模組 {module_name} 未安裝，正在安裝...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
        return False
    return True

def main():
    """主函數"""
    # 檢查關鍵依賴
    modules = ["gunicorn", "flask"]
    for module in modules:
        check_module(module)
    
    # 檢查app.py是否存在
    if not os.path.exists("app.py"):
        print("錯誤: app.py 不存在!")
        sys.exit(1)
    
    # 列出目錄內容進行調試
    print("目前目錄內容:")
    for item in os.listdir("."):
        print(f"- {item}")
    
    # 使用Python模組方式啟動gunicorn
    print("啟動應用...")
    if check_module("gunicorn"):
        from gunicorn.app.wsgiapp import run
        sys.argv = ["gunicorn", "app:app"]
        run()
    else:
        print("無法導入gunicorn，請確保它已正確安裝")
        sys.exit(1)

if __name__ == "__main__":
    main() 