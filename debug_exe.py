# -*- coding: utf-8 -*-
"""
================================================================================
 GameTranslator.exe 崩溃诊断脚本
================================================================================
 用法: 将本文件放在 GameTranslator.exe 同目录下 (dist/)，然后运行:
   python debug_exe.py
================================================================================
"""
import subprocess
import sys
import os
import time

EXE_NAME = "GameTranslator.exe"


def diagnose():
    exe_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(exe_dir, EXE_NAME)

    if not os.path.exists(exe_path):
        print(f"❌ 未找到 {EXE_NAME}")
        print(f"   请将本脚本放在 {EXE_NAME} 所在目录下运行")
        print(f"   当前搜索路径: {exe_dir}")
        sys.exit(1)

    file_size = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"📦 目标文件: {exe_path}")
    print(f"   大小: {file_size:.1f} MB")
    print(f"   运行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 启动 exe 并捕获输出
    try:
        result = subprocess.run(
            [exe_path],
            capture_output=True,
            text=True,
            cwd=exe_dir,
            timeout=30,  # 30 秒超时
        )
        print(f"=== EXIT CODE: {result.returncode} ===")
        if result.stdout.strip():
            print("=== STDOUT ===")
            print(result.stdout)
        if result.stderr.strip():
            print("=== STDERR ===")
            print(result.stderr)
    except subprocess.TimeoutExpired:
        print("⚠️ EXE 在 30 秒内未退出 (GUI 程序正常行为)")
        print("   → 如果 Gui 窗口已出现，说明启动成功")
    except FileNotFoundError:
        print(f"❌ 无法执行 {EXE_NAME} (可能被杀毒软件拦截)")
    except Exception as e:
        print(f"❌ 运行异常: {e}")

    # 检查 error.log
    print("=" * 60)
    log_path = os.path.join(exe_dir, "error.log")
    if os.path.exists(log_path):
        size = os.path.getsize(log_path)
        print(f"📋 error.log 存在 ({size} 字节):")
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                print(content[-2000:])  # 最后 2000 字符
            else:
                print("   (空文件)")
    else:
        print("📋 error.log 不存在 (无异常记录)")

    # 检查 crash_report.txt
    crash_path = os.path.join(exe_dir, "crash_report.txt")
    if os.path.exists(crash_path):
        print(f"\n💥 crash_report.txt 存在:")
        with open(crash_path, "r", encoding="utf-8") as f:
            print(f.read()[:2000])

    # 检查 config.json
    config_path = os.path.join(exe_dir, "config.json")
    if os.path.exists(config_path):
        print(f"\n📋 config.json 已生成 (配置正常)")
    else:
        print(f"\n📋 config.json 未生成 (首次运行正常)")

    print("=" * 60)
    print("诊断完成。如仍有问题，请将以上输出复制给开发者。")
    input("\n按回车键退出...")


if __name__ == "__main__":
    diagnose()