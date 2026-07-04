"""
main_screen.py - 主界面
包含首页(自选股+大盘)、搜索页、详情页、设置页的屏幕管理和导航
"""

import time
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Label, Button, Input, Static,
    ListView, ListItem, TabbedContent, TabPane, DataTable
)
from textual.reactive import reactive
from textual import events
from rich.text import Text
from rich.table import Table
from rich.layout import Layout

from fetcher import (
    fetch_market_overview, fetch_quote, fetch_kline,
    fetch_quotes_batch, search_stocks, MarketOverview, StockQuote, KlineItem
)
from analyzer import calc_all_ma, calc_volatility, calc_current_change
from indicator_engine import analyze, FourLampResult
from database import (
    get_watchlist, add_watchlist, remove_watchlist, is_in_watchlist,
    get_search_history, add_search_history, get_refresh_interval,
    set_refresh_interval, update_watchlist_name, get_setting, set_setting
)
from scheduler import get_scheduler, StockScheduler


# ─── 工具函数 ─────────────────────────────────────────────────────────

def format_price(val: float) -> str:
    if val >= 10000:
        return f"{val/10000:.2f}万"
    return f"{val:.2f}"


def format_amount(val: float) -> str:
    if val >= 100000000:
        return f"{val/100000000:.2f}亿"
    elif val >= 10000:
        return f"{val/10000:.2f}万"
    return f"{val:.2f}"


def format_change(val: float) -> str:
    if val > 0:
        return f"+{val:.2f}"
    elif val < 0:
        return f"{val:.2f}"
    return "0.00"


def make_lamp_text(result: FourLampResult) -> tuple[str, list[str]]:
    """生成指示灯文本和颜色列表"""
    labels = ["区间", "走势", "板块", "量价"]
    colors = []
    parts = []
    for i, (label, val) in enumerate(zip(labels, [
        result.qujian, result.zoushi, result.bankuai, result.liangjia
    ])):
        c = "red" if val else "green"
        colors.append(c)
        sym = "●" if val else "○"
        parts.append(f"[{c}]{label}{sym}[/]")
    return " | ".join(parts), colors


def render_kline(kline_data: list[KlineItem], width: int = 50, height: int = 12) -> str:
    """用字符绘制简易K线图"""
    if not kline_data or len(kline_data) < 2:
        return "数据不足，无法绘制K线图"

    # 取最后width个数据
    data = kline_data[-width:] if len(kline_data) > width else kline_data
    n = len(data)

    prices = [item.close_p for item in data]
    highs = [item.high_p for item in data]
    lows = [item.low_p for item in data]

    min_p = min(lows)
    max_p = max(highs)
    diff = max_p - min_p
    if diff == 0:
        diff = 1

    lines = []
    for row in range(height):
        line_chars = []
        # 计算当前行对应的价位
        price_level = max_p - (diff * row / (height - 1))
        for col in range(n):
            item = data[col]
            high = item.high_p
            low = item.low_p
            open_p = item.open_p
            close = item.close_p

            is_up = close >= open_p
            # 判断蜡烛图各部分
            candle_top = max(open_p, close)
            candle_bot = min(open_p, close)

            if price_level <= high and price_level >= low:
                if price_level <= candle_top and price_level >= candle_bot:
                    line_chars.append("█" if is_up else "▓")
                else:
                    line_chars.append("│")
            else:
                line_chars.append(" ")

        lines.append("".join(line_chars))

    # Y轴标签
    y_labels = []
    for i in range(height):
        if i % 2 == 0:
            val = max_p - (diff * i / (height - 1))
            y_labels.append(f"{val:>8.2f} ")
        else:
            y_labels.append("         ")
    
    result_lines = []
    for i, (label, line) in enumerate(zip(y_labels, lines)):
        result_lines.append(f"{label}{line}")

    # X轴日期
    step = max(1, n // 8)
    x_labels = ""
    for i in range(n):
        if i % step == 0:
            x_labels += data[i].date[-5:] if len(data[i].date) >= 5 else data[i].date
            x_labels += " " * (step - 1) if step > 1 else ""
        else:
            x_labels += " "

    result_lines.append(f"         {x_labels}")
    return "\n".join(result_lines)


# ─── 大盘概况组件 ─────────────────────────────────────────────────────

class MarketBar(Static):
    """大盘概况显示条"""

    market_data: Optional[MarketOverview] = None

    def on_mount(self):
        self.refresh_market()

    def refresh_market(self):
        self.market_data = fetch_market_overview()
        self.refresh()

    def render(self) -> str:
        if not self.market_data:
            return "正在获取大盘数据..."
        m = self.market_data
        sh_c = f"[red]▲ {m.sh_change_pct:+.2f}%[/]" if m.sh_change_pct > 0 else \
               f"[green]▼ {m.sh_change_pct:+.2f}%[/]" if m.sh_change_pct < 0 else \
               f"━ {m.sh_change_pct:+.2f}%"
        sz_c = f"[red]▲ {m.sz_change_pct:+.2f}%[/]" if m.sz_change_pct > 0 else \
               f"[green]▼ {m.sz_change_pct:+.2f}%[/]" if m.sz_change_pct < 0 else \
               f"━ {m.sz_change_pct:+.2f}%"
        cy_c = f"[red]▲ {m.cy_change_pct:+.2f}%[/]" if m.cy_change_pct > 0 else \
               f"[green]▼ {m.cy_change_pct:+.2f}%[/]" if m.cy_change_pct < 0 else \
               f"━ {m.cy_change_pct:+.2f}%"
        return (
            f"  {m.sh_name} {m.sh_price:.2f} {sh_c}  │  "
            f"{m.sz_name} {m.sz_price:.2f} {sz_c}  │  "
            f"{m.cy_name} {m.cy_price:.2f} {cy_c}"
        )


# ─── 首页 - 自选股列表 ────────────────────────────────────────────────

class HomeScreen(Screen):
    """首页：自选股列表 + 大盘概况"""

    def compose(self) -> ComposeResult:
        yield MarketBar(id="market-bar")
        with Container(id="watchlist-container"):
            yield Static("【自选股列表】", classes="section-title")
            yield Static("加载中...", id="watchlist-content")
        yield Static("", id="status-bar")

    def on_mount(self):
        self.refresh_watchlist()

    def refresh_watchlist(self):
        """刷新自选股列表"""
        watchlist = get_watchlist()
        content = self.query_one("#watchlist-content", Static)
        if not watchlist:
            content.update("暂无自选股，请前往搜索页添加")
            return

        lines = []
        codes = [item["code"] for item in watchlist]
        quotes = fetch_quotes_batch(codes)

        for idx, item in enumerate(watchlist):
            q = quotes[idx] if idx < len(quotes) else None
            code = item["code"]
            name = item["name"]

            if q:
                price_str = f"{q.price:.2f}"
                change_str = format_change(q.change_pct)
                if q.change_pct > 0:
                    change_str = f"[red]{change_str}%[/]"
                elif q.change_pct < 0:
                    change_str = f"[green]{change_str}%[/]"
                else:
                    change_str = f"{change_str}%"

                # 获取四灯结果
                try:
                    kline = fetch_kline(code, days=30)
                    result = analyze(code, kline, q)
                    lamp_text, _ = make_lamp_text(result)
                except Exception:
                    lamp_text = "数据获取中..."
            else:
                price_str = "--"
                change_str = "--"
                lamp_text = ""

            lines.append(
                f" {code}  {name:<8}  价格: {price_str:>8}  涨跌: {change_str:>10}  {lamp_text}"
            )

        content.update("\n".join(lines))

    def on_click(self, event: events.Click):
        """点击个股进入详情页"""
        # 获取点击位置对应的股票代码
        widget = self.query_one("#watchlist-container", Container)
        # 简单实现：通过点击坐标判断
        try:
            y = event.y
            watchlist = get_watchlist()
            if y < len(watchlist):
                item = watchlist[y]
                self.app.current_code = item["code"]
                self.app.current_name = item["name"]
                self.app.push_screen("detail")
        except Exception:
            pass


# ─── 搜索页 ───────────────────────────────────────────────────────────

class SearchScreen(Screen):
    """搜索页：按名称/代码搜索股票"""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="输入股票名称或代码搜索...", id="search-input")
        with ScrollableContainer(id="search-results"):
            yield Static("输入关键词开始搜索", id="search-info")

    def on_input_submitted(self, event: Input.Submitted):
        self.do_search(event.value)

    def on_input_changed(self, event: Input.Changed):
        keyword = event.value.strip()
        if len(keyword) >= 2:
            self.do_search(keyword)

    def do_search(self, keyword: str):
        """执行搜索"""
        if not keyword or len(keyword) < 1:
            return
        add_search_history(keyword)
        results = search_stocks(keyword)
        container = self.query_one("#search-results", ScrollableContainer)
        info = self.query_one("#search-info", Static)

        if not results:
            info.update(f"未找到与 '{keyword}' 相关的股票")
            return

        lines = []
        for item in results:
            code = item["code"]
            name = item["name"]
            in_wl = "★" if is_in_watchlist(code) else "☆"
            lines.append(f" {in_wl} {code}  {name}")

        info.update(f"找到 {len(results)} 个结果：\n" + "\n".join(lines))

    def on_click(self, event: events.Click):
        """点击搜索结果"""
        try:
            container = self.query_one("#search-results", ScrollableContainer)
            content = self.query_one("#search-info", Static)
            text = content.render()
            if isinstance(text, str):
                lines = text.split("\n")
                # 跳过标题行
                for line in lines[1:]:
                    if "☆" in line or "★" in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            code = parts[1] if len(parts[1]) >= 6 else parts[2]
                            # 提取6位代码
                            import re
                            codes = re.findall(r'\d{6}', line)
                            if codes:
                                code = codes[0]
                                self.app.current_code = code
                                self.app.current_name = parts[-1] if len(parts) > 2 else code
                                self.app.push_screen("detail")
                            break
        except Exception:
            pass


# ─── 详情页 ───────────────────────────────────────────────────────────

class DetailScreen(Screen):
    """详情页：个股行情+K线+四灯+指标摘要"""

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="detail-container"):
            yield Static("加载中...", id="detail-content")

    def on_mount(self):
        self.refresh_detail()

    def refresh_detail(self):
        """刷新详情页数据"""
        code = self.app.current_code
        name = self.app.current_name

        if not code:
            self.query_one("#detail-content", Static).update("请先选择股票")
            return

        quote = fetch_quote(code)
        kline = fetch_kline(code, days=30)
        result = analyze(code, kline, quote)

        lines = []

        # ── 头部信息 ──
        if quote:
            market = "沪" if quote.market == "SH" else "深" if quote.market == "SZ" else "北"
            sign = quote.color_sign
            change_str = format_change(quote.change_pct)
            lines.append(f"【{quote.name} ({quote.code})】{market}")
            lines.append(f"  {sign} 当前价: [bold]{quote.price:.2f}[/]  ")
            if quote.change_pct > 0:
                lines.append(f"  涨跌: [red]{change_str}%▲[/]")
            elif quote.change_pct < 0:
                lines.append(f"  涨跌: [green]{change_str}%▼[/]")
            else:
                lines.append(f"  涨跌: {change_str}%━")
            lines.append(f"  最高: {quote.high:.2f}  最低: {quote.low:.2f}  开盘: {quote.open_p:.2f}")
            lines.append(f"  昨收: {quote.pre_close:.2f}")
            lines.append(f"  成交量: {format_amount(quote.volume)}手  成交额: {format_amount(quote.amount)}")
            lines.append(f"  换手率: {quote.turnover_rate:.2f}%  振幅: {quote.amplitude:.2f}%")
            lines.append(f"  市盈率: {quote.pe:.2f}  市净率: {quote.pb:.2f}")
        else:
            lines.append(f"【{name or code}】")
            lines.append("  无法获取行情数据")

        lines.append("")

        # ── K线图 ──
        lines.append("═══ K线简图 ═══")
        kline_str = render_kline(kline, width=45, height=10)
        lines.append(kline_str)
        lines.append("")

        # ── 四灯指示系统 ──
        lines.append("═══ 四灯决策指示 ═══")
        lamp_text, lamp_colors = make_lamp_text(result)
        lines.append(f"  {lamp_text}")
        lines.append(f"  指示灯: ", end="")
        for i, (label, val) in enumerate(zip(
            ["区间", "走势", "板块", "量价"],
            [result.qujian, result.zoushi, result.bankuai, result.liangjia]
        )):
            c = "red" if val else "green"
            sym = "●" if val else "○"
            lines.append(f"[{c}]{label}:{sym} [/]")
        lines.append("")
        lines.append(f"  ▶ 综合信号: [bold]{result.signal}[/]")
        lines.append("")

        # ── 技术指标摘要 ──
        lines.append("═══ 技术指标摘要 ═══")
        ma_data = calc_all_ma(kline)
        lines.append(f"  MA5: {ma_data.get('ma5', '--'):>8}  MA10: {ma_data.get('ma10', '--'):>8}  MA20: {ma_data.get('ma20', '--'):>8}")
        vol = calc_volatility(kline, 20)
        lines.append(f"  20日波动率: {vol}%" if vol else "  20日波动率: --")
        if len(kline) >= 2:
            latest_chg = kline[-1].change_pct
            chg_str = f"[red]{latest_chg:+.2f}%[/]" if latest_chg > 0 else \
                      f"[green]{latest_chg:+.2f}%[/]" if latest_chg < 0 else \
                      f"{latest_chg:.2f}%"
            lines.append(f"  日涨跌幅: {chg_str}")
        lines.append("")

        # ── 操作按钮 ──
        is_watched = is_in_watchlist(code)
        lines.append(f"  {'★ 已在自选股' if is_watched else '☆ 加入自选股'}  |  [B]返回首页[/]")

        content = self.query_one("#detail-content", Static)
        content.update("\n".join(lines))

    def on_click(self, event: events.Click):
        """处理点击事件"""
        try:
            # 检查是否点击了加入/移除自选股
            content = self.query_one("#detail-content", Static)
            text = str(content.render())
            code = self.app.current_code

            if "☆ 加入自选股" in text:
                add_watchlist(code, self.app.current_name)
                self.refresh_detail()
            elif "★ 已在自选股" in text:
                remove_watchlist(code)
                self.refresh_detail()
            elif "返回首页" in text:
                self.app.pop_screen()
        except Exception:
            pass


# ─── 设置页 ───────────────────────────────────────────────────────────

class SettingsScreen(Screen):
    """设置页：管理自选股、设定刷新间隔"""

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="settings-container"):
            yield Static("【设置】", classes="section-title")
            yield Static("", id="settings-content")

    def on_mount(self):
        self.refresh_settings()

    def refresh_settings(self):
        """刷新设置页面"""
        lines = []

        # 刷新间隔
        current_interval = get_refresh_interval()
        interval_label = get_setting("refresh_interval_label", "1分钟")
        lines.append(f"═══ 刷新设置 ═══")
        lines.append(f"  当前间隔: {interval_label} ({current_interval}秒)")
        lines.append("")
        lines.append("  [30秒]  [1分钟]  [5分钟]")
        lines.append("")

        # 自选股管理
        lines.append("═══ 自选股管理 ═══")
        watchlist = get_watchlist()
        if watchlist:
            for i, item in enumerate(watchlist):
                code = item["code"]
                name = item["name"]
                lines.append(f"  [{i+1}] {code}  {name}  [删除]")
        else:
            lines.append("  暂无自选股")
        lines.append("")
        lines.append("  [B]返回首页[/]")

        content = self.query_one("#settings-content", Static)
        content.update("\n".join(lines))

    def on_click(self, event: events.Click):
        """处理点击事件"""
        try:
            content = self.query_one("#settings-content", Static)
            text = str(content.render())

            # 切换刷新间隔
            if "[30秒]" in text and "30秒" in str(event):
                set_refresh_interval(30)
                s = get_scheduler()
                s.set_interval(30)
                self.refresh_settings()
            elif "[1分钟]" in text and "1分钟" in str(event):
                set_refresh_interval(60)
                s = get_scheduler()
                s.set_interval(60)
                self.refresh_settings()
            elif "[5分钟]" in text and "5分钟" in str(event):
                set_refresh_interval(300)
                s = get_scheduler()
                s.set_interval(300)
                self.refresh_settings()
            elif "[删除]" in text:
                # 删除自选股
                watchlist = get_watchlist()
                lines = text.split("\n")
                for line in lines:
                    if "[删除]" in line and "  " in line:
                        parts = line.strip().split()
                        for p in parts:
                            if len(p) == 6 and p.isdigit():
                                remove_watchlist(p)
                                self.refresh_settings()
                                return
            elif "返回首页" in text:
                self.app.pop_screen()
        except Exception:
            pass


# ─── 主屏幕（Tab导航）───────────────────────────────────────────────

class StockMainScreen(Screen):
    """主屏幕 - 包含Tab导航页面"""

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="home"):
            with TabPane("首页", id="home"):
                yield HomeScreen()
            with TabPane("搜索", id="search"):
                yield SearchScreen()
            with TabPane("详情", id="detail"):
                yield DetailScreen()
            with TabPane("设置", id="settings"):
                yield SettingsScreen()

    def on_mount(self):
        # 注册定时刷新
        scheduler = get_scheduler()
        scheduler.register_callback(self.auto_refresh)

    def auto_refresh(self):
        """定时刷新回调"""
        try:
            home = self.query_one(HomeScreen)
            home.refresh_watchlist()
            # 如果当前在详情页也刷新
            try:
                detail = self.query_one(DetailScreen)
                detail.refresh_detail()
            except Exception:
                pass
        except Exception:
            pass
