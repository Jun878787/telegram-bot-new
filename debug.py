#!/usr/bin/env python3
"""
調試腳本 - 用於在Render上收集環境信息和診斷問題
"""
import os
import sys
import platform
import subprocess
import importlib.util
import traceback

def print_section(title):
    """打印帶有分隔線的章節標題"""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def run_command(cmd):
    """運行命令並返回輸出"""
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"錯誤 (代碼 {e.returncode}):\n{e.output}"

def check_directory_structure():
    """檢查目錄結構"""
    print_section("目錄結構")
    cwd = os.getcwd()
    print(f"當前工作目錄: {cwd}")
    
    print("\n所有文件和目錄:")
    for root, dirs, files in os.walk(".", topdown=True):
        level = root.count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            print(f"{sub_indent}{file}")

def check_python_modules():
    """檢查Python模組"""
    print_section("Python模組")
    
    # 列出已安裝的包
    try:
        pip_list = run_command(f"{sys.executable} -m pip list")
        print("已安裝的Python包:\n")
        print(pip_list)
    except Exception as e:
        print(f"列出包時出錯: {str(e)}")
    
    # 檢查關鍵模組
    critical_modules = ["flask", "gunicorn", "telebot", "psutil"]
    print("\n關鍵模組檢查:")
    for module in critical_modules:
        spec = importlib.util.find_spec(module)
        if spec is None:
            print(f"❌ {module} - 未安裝")
        else:
            try:
                mod = importlib.import_module(module)
                version = getattr(mod, "__version__", "未知")
                print(f"✅ {module} - 已安裝 (版本: {version})")
            except Exception as e:
                print(f"⚠️ {module} - 已安裝但無法導入: {str(e)}")

def check_app_modules():
    """檢查應用程式模組"""
    print_section("應用程式模組")
    
    # 檢查app.py
    if os.path.exists("app.py"):
        print("✅ app.py 存在")
        try:
            with open("app.py", "r") as f:
                content = f.read()
                print("\napp.py 內容摘要:")
                print("----------------")
                print("\n".join(content.split("\n")[:20]) + "\n...")
                if "app = Flask" in content:
                    print("\n✅ 找到Flask應用定義")
                else:
                    print("\n❌ 未找到Flask應用定義")
        except Exception as e:
            print(f"讀取app.py時出錯: {str(e)}")
    else:
        print("❌ app.py 不存在")
    
    # 嘗試導入app
    print("\n嘗試導入app模組:")
    try:
        import app
        print(f"✅ 成功導入app模組")
        if hasattr(app, 'app'):
            print(f"✅ app模組有app變數")
        else:
            print(f"❌ app模組沒有app變數")
    except Exception as e:
        print(f"❌ 導入app模組時出錯: {str(e)}")
        traceback.print_exc()

def check_network():
    """檢查網絡連接"""
    print_section("網絡連接")
    
    # 檢查DNS解析
    print("DNS解析檢查:")
    domains = ["api.telegram.org", "render.com", "github.com"]
    for domain in domains:
        try:
            output = run_command(f"python -c \"import socket; print(socket.gethostbyname('{domain}'))\"")
            print(f"✅ {domain} -> {output.strip()}")
        except Exception as e:
            print(f"❌ {domain} -> 解析失敗: {str(e)}")
    
    # 檢查端口監聽
    print("\n端口監聽檢查:")
    try:
        output = run_command("netstat -tuln")
        print(output)
    except Exception as e:
        print(f"無法獲取網絡連接: {str(e)}")

def check_environment():
    """檢查環境變數"""
    print_section("環境變數")
    
    # 重要的環境變數
    important_vars = [
        "PORT", "BOT_TOKEN", "ADMIN_ID", "TARGET_GROUP_ID", 
        "PYTHONPATH", "DATA_FILE", "USER_SETTINGS_FILE"
    ]
    
    for var in important_vars:
        value = os.environ.get(var, "未設置")
        if var == "BOT_TOKEN" and value != "未設置":
            # 隱藏敏感信息
            masked_value = value[:5] + "..." + value[-3:] if len(value) > 8 else "***"
            print(f"{var}: {masked_value}")
        else:
            print(f"{var}: {value}")
    
    # Python路徑
    print(f"\nPython路徑:")
    for p in sys.path:
        print(f"  {p}")

def main():
    """主函數"""
    try:
        print_section("調試開始")
        print(f"時間: {__import__('datetime').datetime.now()}")
        print(f"Python版本: {sys.version}")
        print(f"平台: {platform.platform()}")
        print(f"系統: {platform.system()} {platform.release()}")
        
        # 執行各種檢查
        check_environment()
        check_directory_structure()
        check_python_modules()
        check_app_modules()
        check_network()
        
        # 檢查gunicorn能否運行
        print_section("Gunicorn測試")
        try:
            output = run_command("which gunicorn || echo 'Not found'")
            print(f"Gunicorn位置: {output.strip()}")
            
            output = run_command("gunicorn --version || echo 'Error'")
            print(f"Gunicorn版本: {output.strip()}")
        except Exception as e:
            print(f"執行gunicorn命令時出錯: {str(e)}")
        
        print_section("調試結束")
        print("所有調試信息收集完成")
        
    except Exception as e:
        print(f"調試過程中發生錯誤: {str(e)}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 