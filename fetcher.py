"""
fetcher.py - 东方财富公开行情接口封装
支持A股实时行情查询、股票名称/代码模糊搜索、K线数据获取、大盘概况
"""

import re
import json
import time
from typing import Optional
from dataclasses import dataclass, field

import requests


# ─── 常量 ─────────────────────────────────────────────────────────────

EASTMONEY_CLIST_URL = "http://80.push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_QUOTE_URL = "http://push2.eastmoney.com/api/qt/stock/get"
EASTMONEY_KLINE_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_SEARCH_URL = "http://searchadapter.eastmoney.com/api/suggest/get_search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": "http://quote.eastmoney.com/",
}


# ─── 数据结构 ──────────────────────────────────────────────────────────

@dataclass
class StockQuote:
    """个股实时行情"""
    code: str
    name: str
    price: float          # 当前价
    change: float         # 涨跌额
    change_pct: float     # 涨跌幅 %
    high: float           # 最高
    low: float            # 最低
    open_p: float         # 开盘
    pre_close: float      # 昨收
    volume: float         # 成交量(手)
    amount: float         # 成交额(元)
    turnover_rate: float = 0.0   # 换手率 %
    amplitude: float = 0.0       # 振幅 %
    pe: float = 0.0              # 市盈率
    pb: float = 0.0              # 市净率
    timestamp: int = 0

    @property
    def market(self) -> str:
        if self.code.startswith(("60", "68")):
            return "SH"
        elif self.code.startswith(("00", "30", "02", "39")):
            return "SZ"
        elif self.code.startswith(("4", "8")):
            return "BJ"
        return "??"

    @property
    def color_sign(self) -> str:
        """涨跌颜色符号"""
        if self.change_pct > 0:
            return "▲"
        elif self.change_pct < 0:
            return "▼"
        return "━"


@dataclass
class KlineItem:
    """K线数据项"""
    date: str
    open_p: float
    close_p: float
    high_p: float
    low_p: float
    volume: float         # 成交量(手)
    amount: float         # 成交额(元)
    change_pct: float = 0.0


@dataclass
class MarketOverview:
    """大盘概况"""
    sh_name: str = "上证指数"
    sh_code: str = "000001"
    sh_price: float = 0.0
    sh_change: float = 0.0
    sh_change_pct: float = 0.0

    sz_name: str = "深证成指"
    sz_code: str = "399001"
    sz_price: float = 0.0
    sz_change: float = 0.0
    sz_change_pct: float = 0.0

    cy_name: str = "创业板指"
    cy_code: str = "399006"
    cy_price: float = 0.0
    cy_change: float = 0.0
    cy_change_pct: float = 0.0


# ─── 工具函数 ──────────────────────────────────────────────────────────

def _fmt_code(code: str) -> str:
    """统一为6位代码"""
    c = code.strip().upper()
    for p in ["SH", "SZ", "BJ"]:
        if c.startswith(p):
            c = c[len(p):]
            break
    return c.zfill(6)[:6]


def _market_flag(code: str) -> int:
    """1=沪 0=深 8=京"""
    if code.startswith(("60", "68")) or code == "000001":
        return 1
    if code.startswith(("00", "30", "02", "39")):
        return 0
    if code.startswith(("4", "8")):
        return 8
    return 1


def _secid(code: str) -> str:
    return f"{_market_flag(code)}.{code}"


def _pv(val) -> float:
    """安全转浮点"""
    if val in (None, "-", "", "--"):
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# ─── 核心API ───────────────────────────────────────────────────────────

def fetch_market_overview() -> MarketOverview:
    """获取大盘概况"""
    mo = MarketOverview()
    targets = [
        ("000001", 1, "上证指数"),
        ("399001", 0, "深证成指"),
        ("399006", 0, "创业板指"),
    ]
    fields = "f2,f3,f4,f12,f14"
    for code, mt, _ in targets:
        try:
            params = {
                "pn": 1, "pz": 1, "po": 1, "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2, "invt": 2, "fid": "f3",
                "fs": f"m:0+t:{mt}+s:{code}",
                "fields": fields,
            }
            resp = requests.get(EASTMONEY_CLIST_URL, params=params, headers=HEADERS, timeout=10)
            data = resp.json()
            if data.get("data") and data["data"].get("diff"):
                it = data["data"]["diff"][0]
                price = _pv(it.get("f2"))
                cp = _pv(it.get("f3"))
                chg = _pv(it.get("f4"))
                if mt == 1:
                    mo.sh_price = price
                    mo.sh_change_pct = cp
                    mo.sh_change = chg
                elif code == "399001":
                    mo.sz_price = price
                    mo.sz_change_pct = cp
                    mo.sz_change = chg
                elif code == "399006":
                    mo.cy_price = price
                    mo.cy_change_pct = cp
                    mo.cy_change = chg
        except Exception:
            pass
    return mo


def fetch_quote(code: str) -> Optional[StockQuote]:
    """获取个股实时行情"""
    code = _fmt_code(code)
    params = {
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2, "invt": 2,
        "secid": _secid(code),
        "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f24,f25,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f61,f62,f115,f116,f117,f152",
    }
    try:
        resp = requests.get(EASTMONEY_QUOTE_URL, params=params, headers=HEADERS, timeout=10)
        data = resp.json().get("data")
        if not data:
            return None
        return StockQuote(
            code=str(data.get("f12", code)),
            name=str(data.get("f14", "")),
            price=_pv(data.get("f43") or data.get("f2")),
            change=_pv(data.get("f44") or data.get("f170") or data.get("f4")),
            change_pct=_pv(data.get("f45") or data.get("f3") or data.get("f170")),
            high=_pv(data.get("f44") or data.get("f15")),
            low=_pv(data.get("f45") or data.get("f16")),
            open_p=_pv(data.get("f46") or data.get("f17")),
            pre_close=_pv(data.get("f47") or data.get("f18")),
            volume=_pv(data.get("f5") or data.get("f47")),
            amount=_pv(data.get("f6") or data.get("f48")),
            turnover_rate=_pv(data.get("f168") or data.get("f38")),
            amplitude=_pv(data.get("f8") or data.get("f37")),
            pe=_pv(data.get("f9") or data.get("f39")),
            pb=_pv(data.get("f12") or data.get("f23") or data.get("f34")),
            timestamp=int(time.time()),
        )
    except Exception as e:
        print(f"[fetcher] 获取 {code} 失败: {e}")
        return None


def fetch_quotes_batch(codes: list[str]) -> list:
    """批量获取行情"""
    results = []
    for code in codes:
        q = fetch_quote(code)
        results.append(q)
        time.sleep(0.08)
    return results


def search_stocks(keyword: str) -> list[dict]:
    """模糊搜索股票"""
    keyword = keyword.strip()
    if not keyword:
        return []
    results = []
    seen = set()

    # 方法1: 东方财富搜索接口
    try:
        params = {"keyword": keyword, "count": 15, "type": 1}
        resp = requests.get(EASTMONEY_SEARCH_URL, params=params, headers=HEADERS, timeout=8)
        data = resp.json()
        if data.get("QuotationCodeTable"):
            for item in data["QuotationCodeTable"].get("Data", []):
                c = item.get("Code", "")
                if c not in seen:
                    seen.add(c)
                    results.append({"code": c, "name": item.get("Name", ""), "type": "A股"})
    except Exception:
        pass

    # 方法2: 从全市场列表筛选
    if len(results) < 5:
        try:
            params = {
                "pn": 1, "pz": 100, "po": 1, "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2, "invt": 2, "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f12,f14,f3",
            }
            resp = requests.get(EASTMONEY_CLIST_URL, params=params, headers=HEADERS, timeout=10)
            data = resp.json()
            if data.get("data") and data["data"].get("diff"):
                for it in data["data"]["diff"]:
                    c = str(it.get("f12", ""))
                    n = str(it.get("f14", ""))
                    if c not in seen and (keyword.lower() in c.lower() or keyword in n):
                        seen.add(c)
                        results.append({"code": c, "name": n, "type": "A股"})
        except Exception:
            pass

    return results[:30]


def fetch_kline(code: str, days: int = 30) -> list[KlineItem]:
    """获取日K线数据"""
    code = _fmt_code(code)
    params = {
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "secid": _secid(code),
        "beg": "0",
        "end": "20500101",
        "lmt": str(days + 10),
    }
    try:
        resp = requests.get(EASTMONEY_KLINE_URL, params=params, headers=HEADERS, timeout=10)
        data = resp.json().get("data", {}).get("klines", [])
        if not data:
            return []
        items = []
        for line in data[-days:]:
            parts = line.split(",")
            if len(parts) >= 11:
                try:
                    item = KlineItem(
                        date=parts[0],
                        open_p=float(parts[1]),
                        close_p=float(parts[2]),
                        high_p=float(parts[3]),
                        low_p=float(parts[4]),
                        volume=float(parts[5]) / 100,
                        amount=float(parts[6]),
                    )
                    items.append(item)
                except (ValueError, IndexError):
                    continue
        for i in range(len(items)):
            if i > 0 and items[i-1].close_p != 0:
                items[i].change_pct = ((items[i].close_p - items[i-1].close_p) / items[i-1].close_p) * 100
        return items
    except Exception as e:
        print(f"[fetcher] K线获取失败 {code}: {e}")
        return []
