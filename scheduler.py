"""
scheduler.py - 定时任务调度器
支持设置定时自动刷新（30秒/1分钟/5分钟可选）
支持回调函数注册
"""

import time
import threading
from typing import Callable, Optional


class StockScheduler:
    """
    定时刷新调度器
    用法:
        s = StockScheduler()
        s.set_interval(60)  # 60秒
        s.register_callback(my_refresh_func)
        s.start()
        ...
        s.stop()
    """

    def __init__(self, interval_seconds: int = 60):
        self._interval = interval_seconds
        self._callbacks: list[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def interval(self) -> int:
        return self._interval

    def set_interval(self, seconds: int):
        """设置刷新间隔（秒）"""
        if seconds < 10:
            seconds = 10
        self._interval = seconds

    def register_callback(self, callback: Callable):
        """注册刷新回调函数"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """取消注册回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _loop(self):
        """调度器主循环"""
        while not self._stop_event.is_set():
            self._stop_event.wait(self._interval)
            if self._stop_event.is_set():
                break
            for cb in self._callbacks:
                try:
                    cb()
                except Exception as e:
                    print(f"[scheduler] 回调执行错误: {e}")

    def start(self):
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="StockScheduler")
        self._thread.start()

    def stop(self):
        """停止调度器"""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def is_running(self) -> bool:
        return self._running

    def refresh_now(self):
        """立即执行所有回调"""
        for cb in self._callbacks:
            try:
                cb()
            except Exception as e:
                print(f"[scheduler] 立即刷新回调错误: {e}")


# 全局调度器实例
_global_scheduler: Optional[StockScheduler] = None


def get_scheduler() -> StockScheduler:
    """获取全局调度器"""
    global _global_scheduler
    if _global_scheduler is None:
        from database import get_refresh_interval
        interval = get_refresh_interval()
        _global_scheduler = StockScheduler(interval)
    return _global_scheduler


def refresh_all_watchlist():
    """
    刷新所有自选股数据的默认回调
    会被UI层覆盖实现
    """
    pass
