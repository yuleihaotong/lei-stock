"""
main.py - A股短线决策辅助工具 主入口
运行在 Termux / 任何终端环境
"""

import sys
import os

# 确保项目根目录在导入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from scheduler import get_scheduler


def main():
    """主入口"""
    # 初始化数据库
    print("📊 初始化数据库...")
    init_db()

    # 启动调度器
    print("⏱️  启动定时调度器...")
    scheduler = get_scheduler()
    scheduler.start()

    # 启动Textual应用
    print("🚀 启动终端界面...")
    from app import StockToolApp
    app = StockToolApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 正在退出...")
    finally:
        scheduler.stop()
        print("✅ 已安全退出")


if __name__ == "__main__":
    main()
