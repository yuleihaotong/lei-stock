"""
main_android.py - Android APK 主入口
启动Flask API服务 + WebView前端界面
"""

import os
import sys
import time
import threading

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from database import init_db
from scheduler import get_scheduler
from web_api import start_api


# ─── Android WebView 桥接 ──────────────────────────────────────────
# 通过 Python-for-Android 的 android 模块与 Java WebView 通信
# 如果不可用（开发环境），则使用纯文本提示

try:
    from android import activity, mActivity
    import android
    ANDROID_AVAILABLE = True
except ImportError:
    ANDROID_AVAILABLE = False


def get_data_dir() -> str:
    """获取应用数据目录"""
    if ANDROID_AVAILABLE:
        try:
            return mActivity.getFilesDir().getAbsolutePath()
        except Exception:
            pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def start_backend():
    """启动后端服务"""
    # 初始化数据库
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    os.chdir(data_dir)
    print(f"[main] 数据目录: {data_dir}")

    init_db()
    print("[main] 数据库初始化完成")

    # 启动调度器
    scheduler = get_scheduler()
    scheduler.start()
    print("[main] 调度器已启动")

    # 启动API服务
    api = start_api(host="127.0.0.1", port=5000)
    print("[main] API服务已启动: http://127.0.0.1:5000")

    return api


def load_webview():
    """加载WebView界面（Android专用）"""
    if not ANDROID_AVAILABLE:
        print("[main] 非Android环境，跳过WebView加载")
        print("[main] API服务运行在 http://127.0.0.1:5000")
        print("[main] 在前端目录运行: cd frontend && python -m http.server 8080")
        return

    try:
        # 获取前端HTML路径
        frontend_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "frontend"
        )
        index_path = os.path.join(frontend_dir, "index.html")

        # 如果前端文件不存在，使用内置HTML
        if not os.path.exists(index_path):
            print("[main] 前端文件未找到，使用内置界面")
            return

        # 通过Android的WebView加载
        file_url = f"file://{index_path}"
        # 这个调用需要Java层配合
        print(f"[main] 加载WebView: {file_url}")

        # 通过JNI调用Java方法
        try:
            # Python-for-Android方式
            python_activity = mActivity
            # 获取WebView并加载页面
            webview = python_activity.findViewById(
                python_activity.getResources().getIdentifier(
                    "webview", "id", python_activity.getPackageName()
                )
            )
            if webview:
                webview.getSettings().setJavaScriptEnabled(True)
                webview.getSettings().setDomStorageEnabled(True)
                # 允许加载本地文件
                webview.getSettings().setAllowFileAccess(True)
                webview.loadUrl(f"http://127.0.0.1:5000/")
        except Exception as e:
            print(f"[main] WebView加载失败: {e}")
    except Exception as e:
        print(f"[main] WebView错误: {e}")


def open_browser_fallback():
    """开发环境下打开浏览器访问API"""
    import webbrowser
    time.sleep(1)
    # 如果前端服务在运行
    try:
        webbrowser.open("http://127.0.0.1:5000/")
    except Exception:
        pass


def main():
    """Android主入口"""
    print("=" * 40)
    print("  A股短线决策辅助工具")
    print("  四灯决策指示系统")
    print("=" * 40)

    # 启动后端
    start_backend()

    # 加载WebView
    load_webview()

    # 如果不是Android，打开浏览器
    if not ANDROID_AVAILABLE:
        print()
        print("=" * 40)
        print("  🌐 请在浏览器中访问:")
        print("  http://127.0.0.1:5000/")
        print()
        print("  💡 或者启动前端:")
        print("  cd frontend && python -m http.server 8080")
        print("  然后访问: http://127.0.0.1:8080/")
        print("=" * 40)
        # 开发环境下可选项
        # open_browser_fallback()

    # 保持主线程运行
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[main] 正在关闭...")
        from web_api import stop_api
        stop_api()
        scheduler = get_scheduler()
        scheduler.stop()
        print("[main] 已安全退出")


if __name__ == "__main__":
    main()
