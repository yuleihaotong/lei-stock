"""
app.py - 主入口文件
启动textual终端UI，初始化定时任务和数据库
"""

import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from textual.app import App
from ui.main_screen import StockMainScreen


class StockToolApp(App):
    """A股短线决策辅助工具 - 主应用"""

    TITLE = "A股短线决策辅助工具"
    SUB_TITLE = "四灯决策指示系统"
    CSS = """
    Screen {
        background: $surface;
    }

    /* ── 大盘概况栏 ── */
    #market-bar {
        height: 3;
        dock: top;
        background: $panel;
        padding: 0 1;
    }
    #market-bar > Label {
        padding: 0 1;
    }

    /* ── 底部状态栏 ── */
    #status-bar {
        height: 1;
        dock: bottom;
        background: $panel;
        content-align: center middle;
        color: $text-muted;
    }

    /* ── 标签页切换 ── */
    #tab-bar {
        dock: top;
        height: 3;
        background: $boost;
    }
    #tab-bar > Button {
        width: 1fr;
    }

    /* ── 自选股列表 ── */
    #watchlist-container {
        height: 1fr;
        overflow-y: auto;
    }
    .stock-card {
        height: 3;
        background: $surface;
        border: solid $border;
        margin: 0 1;
    }
    .stock-card:hover {
        background: $boost;
    }
    .stock-code {
        width: 10;
        padding: 0 1;
    }
    .stock-name {
        width: 12;
        padding: 0 1;
    }
    .stock-price {
        width: 10;
        padding: 0 1;
        text-align: right;
    }
    .stock-change-up {
        width: 10;
        padding: 0 1;
        text-align: right;
        color: #e74c3c;
    }
    .stock-change-down {
        width: 10;
        padding: 0 1;
        text-align: right;
        color: #2ecc71;
    }
    .stock-lamp {
        width: 10;
        padding: 0 1;
        text-align: center;
    }

    /* ── 搜索页 ── */
    #search-input {
        dock: top;
        margin: 1;
    }
    #search-results {
        height: 1fr;
        overflow-y: auto;
    }
    .search-item {
        height: 3;
        padding: 0 1;
    }
    .search-item:hover {
        background: $boost;
    }

    /* ── 详情页 ── */
    #detail-container {
        height: 1fr;
        overflow-y: auto;
    }
    #detail-header {
        height: 5;
        background: $panel;
        padding: 0 1;
    }
    #kline-area {
        height: 20;
        background: $surface;
        border: solid $border;
        margin: 0 1;
    }
    #lamp-area {
        height: 3;
        margin: 0 1;
    }
    .lamp-cell {
        width: 1fr;
        text-align: center;
    }
    .lamp-red {
        color: #e74c3c;
    }
    .lamp-green {
        color: #2ecc71;
    }
    #indicator-summary {
        height: 8;
        background: $surface;
        border: solid $border;
        margin: 0 1;
    }

    /* ── 设置页 ── */
    #settings-container {
        height: 1fr;
        overflow-y: auto;
    }
    .setting-row {
        height: 3;
        padding: 0 1;
    }
    .setting-label {
        width: 20;
    }
    .setting-value {
        width: 1fr;
    }

    /* ── 通用 ── */
    Button {
        background: $primary;
        color: $text;
    }
    Button:hover {
        background: $secondary;
    }
    Button:focus {
        border: thick $accent;
    }
    """

    def __init__(self):
        super().__init__()
        # 数据库初始化
        init_db()
        # 当前选中的股票代码
        self.current_code = ""
        self.current_name = ""

    def compose(self):
        from textual.widgets import Header, Footer
        yield Header()
        yield StockMainScreen()
        yield Footer()

    def on_mount(self):
        """应用挂载完成"""
        # 自动跳转到主界面
        self.push_screen("main")


def main():
    app = StockToolApp()
    app.run()


if __name__ == "__main__":
    main()
