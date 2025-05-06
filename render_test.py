#!/usr/bin/env python3
"""
測試文件，確認 Render 平台可以正確讀取
"""
import os
import sys

def main():
    """主函數"""
    print("===== Render 測試文件 =====")
    print(f"Python 版本: {sys.version}")
    print(f"工作目錄: {os.getcwd()}")
    print(f"目錄內容:")
    for item in os.listdir('.'):
        if os.path.isdir(item):
            print(f"目錄: {item}/")
        else:
            print(f"文件: {item}")

if __name__ == "__main__":
    main() 