#!/usr/bin/env python3
import os
import sys
import subprocess
import importlib.util
import traceback

def check_module(module_name):
    """檢查模組是否已安裝"""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"模組 {module_name} 未安裝，正在安裝...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
            return False
        print(f"模組 {module_name} 已安裝")
        return True
    except Exception as e:
        print(f"檢查模組 {module_name} 時出錯: {str(e)}")
        return False

def check_environment():
    """檢查環境變數和系統信息"""
    print("\n=== 環境檢查 ===")
    print(f"Python版本: {sys.version}")
    print(f"系統平台: {sys.platform}")
    print(f"工作目錄: {os.getcwd()}")
    
    print("\n=== 環境變數 ===")
    for key in ["BOT_TOKEN", "ADMIN_ID", "TARGET_GROUP_ID", "PORT", "PYTHONPATH"]:
        value = os.environ.get(key, "未設置")
        if key == "BOT_TOKEN" and value != "未設置":
            value = value[:5] + "..." # 隱藏敏感信息
        print(f"{key}: {value}")

def check_files():
    """檢查關鍵文件"""
    print("\n=== 文件檢查 ===")
    required_files = ["app.py", "bot.py", "requirements.txt", "wsgi.py"]
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} 存在")
        else:
            print(f"✗ {file} 不存在!")
    
    # 列出目錄內容
    print("\n=== 目錄內容 ===")
    for item in os.listdir("."):
        if os.path.isdir(item):
            print(f"📁 {item}/")
        else:
            print(f"📄 {item}")

def main():
    """主函數"""
    try:
        print("===== Telegram Bot 啟動腳本 =====")
        
        # 檢查環境
        check_environment()
        
        # 檢查文件
        check_files()
        
        # 檢查關鍵依賴
        print("\n=== 依賴檢查 ===")
        modules = ["gunicorn", "flask", "telebot", "psutil"]
        for module in modules:
            check_module(module)
        
        # 檢查app.py是否存在
        if not os.path.exists("app.py"):
            print("錯誤: app.py 不存在!")
            sys.exit(1)
        
        # 確認app.py中有app變數
        print("\n=== 檢查app.py內容 ===")
        with open("app.py", "r") as f:
            content = f.read()
            if "app = Flask" in content:
                print("✓ 找到Flask應用程式")
            else:
                print("✗ 未找到Flask應用程式定義!")
        
        # 嘗試導入app模組
        print("\n=== 嘗試導入app模組 ===")
        try:
            import app
            print(f"✓ 成功導入app模組: {app}")
            if hasattr(app, 'app'):
                print(f"✓ 找到app.app變數: {app.app}")
            else:
                print("✗ app模組中沒有app變數!")
        except Exception as e:
            print(f"✗ 導入app模組時出錯: {str(e)}")
            traceback.print_exc()
        
        # 使用Python模組方式啟動gunicorn
        print("\n=== 啟動應用 ===")
        if check_module("gunicorn"):
            print("使用gunicorn啟動應用...")
            try:
                # 設置WSGI應用的路徑
                os.environ["PYTHONPATH"] = os.getcwd()
                from gunicorn.app.wsgiapp import run
                sys.argv = ["gunicorn", "app:app", "--bind", "0.0.0.0:" + os.environ.get("PORT", "10000"), "--log-level", "debug"]
                print(f"執行命令: {' '.join(sys.argv)}")
                run()
            except Exception as e:
                print(f"啟動gunicorn時出錯: {str(e)}")
                traceback.print_exc()
                # 嘗試備用方案
                try:
                    print("嘗試備用方案: 直接運行Flask應用...")
                    import app
                    port = int(os.environ.get("PORT", 10000))
                    app.app.run(host="0.0.0.0", port=port)
                except Exception as e2:
                    print(f"運行Flask應用時出錯: {str(e2)}")
                    traceback.print_exc()
                    sys.exit(2)
        else:
            print("嘗試直接運行Flask應用...")
            try:
                import app
                port = int(os.environ.get("PORT", 10000))
                app.app.run(host="0.0.0.0", port=port)
            except Exception as e:
                print(f"運行Flask應用時出錯: {str(e)}")
                traceback.print_exc()
                sys.exit(2)
    except Exception as e:
        print(f"啟動腳本執行時出錯: {str(e)}")
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main() 