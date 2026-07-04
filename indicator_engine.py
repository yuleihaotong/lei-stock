"""
indicator_engine.py - 四灯决策指示系统核心逻辑
四个维度：区间、走势、板块、量价
每列指示灯：红色=强势/优势  绿色=弱势/劣势
四灯全红 → "可进场"
任意绿灯 → "考虑离场"
"""

from typing import Optional
from fetcher import StockQuote, KlineItem, fetch_quote, fetch_kline, fetch_quotes_batch
from analyzer import (
    calc_all_ma, calc_volatility, calc_volume_ratio,
    calc_support_resistance, calc_ma_trend,
)


# ─── 四灯判断函数 ─────────────────────────────────────────────────────

def judge_qujian(kline_data: list[KlineItem], quote: Optional[StockQuote] = None) -> bool:
    """
    区间维度（红色=强势）：
    规则：当前价格 > MA10 且 价格在最近20日区间的高位(价格 > (最高+最低)/2)
    即：处于均线上方且在中枢以上 → 红
    """
    if len(kline_data) < 10:
        return False

    ma10 = calc_all_ma(kline_data).get("ma10")
    if ma10 is None:
        return False

    current_price = kline_data[-1].close_p
    sr = calc_support_resistance(kline_data)
    mid = (sr["support"] + sr["resistance"]) / 2

    return current_price > ma10 and current_price > mid


def judge_zoushi(kline_data: list[KlineItem]) -> bool:
    """
    走势维度（红色=强势）：
    规则：
    1. 均线多头排列(MA5 > MA10 > MA20) 或
    2. 近5日涨幅为正 且 价格在MA5之上
    满足任一 → 红
    """
    if len(kline_data) < 20:
        return False

    trend = calc_ma_trend(kline_data)
    if trend == "多头排列":
        return True

    ma5 = calc_all_ma(kline_data).get("ma5")
    if ma5 is None:
        return False

    current_price = kline_data[-1].close_p
    if current_price < ma5:
        return False

    # 近5日累计涨幅
    if len(kline_data) >= 6:
        p5 = kline_data[-6].close_p
        if p5 > 0:
            pct = (current_price - p5) / p5 * 100
            return pct > 0

    return False


def judge_bankuai(code: str, kline_data: list[KlineItem]) -> bool:
    """
    板块维度（红色=强势）：
    规则：使用同板块其他股票的平均表现作为参考
    因为无法直接获取板块数据，用以下替代方案：
    1. 根据代码前缀判断所属市场板块
    2. 取同前缀的"兄弟股票"行情做参考
    3. 简单策略：如果个股自身走势强于大盘（上证/深证）
    简化版：个股涨幅 > 0 且 量比 > 0.8 视为板块效应积极
    """
    if not kline_data or len(kline_data) < 2:
        return False

    # 当日涨跌幅
    latest_change = kline_data[-1].change_pct
    vol_ratio = calc_volume_ratio(kline_data) or 0

    # 量比 > 0.8 且 涨幅非负 或 涨幅跑赢同类中位数
    if vol_ratio > 0.8 and latest_change >= -0.5:
        # 再检查是否连续3日跑赢前一日（相对强度）
        positive_days = 0
        for i in range(max(1, len(kline_data) - 4), len(kline_data)):
            if kline_data[i].change_pct > 0:
                positive_days += 1
        return positive_days >= 2

    return False


def judge_liangjia(kline_data: list[KlineItem], quote: Optional[StockQuote] = None) -> bool:
    """
    量价维度（红色=强势）：
    规则：
    1. 量比 > 1.0（放量）
    2. 当日收阳(close > open) 或 虽收阴但缩量(量比<0.8)
    3. 价涨量增 或 价跌量缩 → 健康量价关系
    """
    if len(kline_data) < 2:
        return False

    vol_ratio = calc_volume_ratio(kline_data) or 0
    latest = kline_data[-1]

    is_yang = latest.close_p >= latest.open_p

    if is_yang and vol_ratio > 0.8:
        return True

    if not is_yang and vol_ratio < 0.8:
        return True

    # 量价配合：收阳且放量
    if is_yang and vol_ratio >= 1.0:
        return True

    # 价涨量增检查（连续2日）
    if len(kline_data) >= 3:
        d1 = kline_data[-2]
        d2 = kline_data[-1]
        if d2.close_p > d1.close_p and d2.volume > d1.volume:
            return True

    return False


# ─── 综合判断 ──────────────────────────────────────────────────────────

class FourLampResult:
    """四灯判断结果"""
    qujian: bool          # 区间：True=红 False=绿
    zoushi: bool          # 走势
    bankuai: bool         # 板块
    liangjia: bool        # 量价
    code: str = ""
    name: str = ""

    def __init__(self, code="", name=""):
        self.code = code
        self.name = name
        self.qujian = False
        self.zoushi = False
        self.bankuai = False
        self.liangjia = False

    @property
    def red_count(self) -> int:
        return sum([self.qujian, self.zoushi, self.bankuai, self.liangjia])

    @property
    def all_red(self) -> bool:
        return self.red_count == 4

    @property
    def any_green(self) -> bool:
        return self.red_count < 4

    @property
    def signal(self) -> str:
        if self.all_red:
            return "【可进场】"
        elif self.red_count >= 3:
            return "【谨慎关注】"
        elif self.red_count >= 2:
            return "【中性观望】"
        else:
            return "【考虑离场】"

    @property
    def detail(self) -> str:
        lamps = []
        lamps.append("🔴" if self.qujian else "🟢")
        lamps.append("🔴" if self.zoushi else "🟢")
        lamps.append("🔴" if self.bankuai else "🟢")
        lamps.append("🔴" if self.liangjia else "🟢")
        return f"{''.join(lamps)} {self.signal}"


def analyze(code: str, kline_data: Optional[list[KlineItem]] = None,
            quote: Optional[StockQuote] = None) -> FourLampResult:
    """
    对一只股票进行四灯分析
    :param code: 股票代码
    :param kline_data: 可传入已有的K线数据，None则自动获取
    :param quote: 可传入已有的行情数据，None则自动获取
    :return: FourLampResult
    """
    result = FourLampResult(code=code)

    if kline_data is None:
        kline_data = fetch_kline(code, days=30)
    if quote is None:
        quote = fetch_quote(code)

    if kline_data:
        result.name = kline_data[-1].date if kline_data else ""
        result.qujian = judge_qujian(kline_data, quote)
        result.zoushi = judge_zoushi(kline_data)
        result.bankuai = judge_bankuai(code, kline_data)
        result.liangjia = judge_liangjia(kline_data, quote)

    if quote and not result.name:
        result.name = quote.name

    return result


def analyze_batch(codes: list[str]) -> list[FourLampResult]:
    """批量分析多只股票"""
    results = []
    for code in codes:
        try:
            kline = fetch_kline(code, days=30)
            quote = fetch_quote(code)
            r = analyze(code, kline, quote)
            results.append(r)
        except Exception as e:
            print(f"[indicator] 分析 {code} 失败: {e}")
            r = FourLampResult(code=code)
            results.append(r)
    return results
