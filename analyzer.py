"""
analyzer.py - 技术指标计算模块
支持：均线(MA5/10/20)、日涨跌幅、20日波动率
"""

from typing import Optional
from fetcher import KlineItem, StockQuote


def calc_ma(kline_data: list[KlineItem], period: int) -> Optional[float]:
    """
    计算移动平均线
    :param kline_data: K线列表（按日期升序，最新的在最后）
    :param period: 周期 5/10/20
    :return: 最新均线值
    """
    if len(kline_data) < period:
        return None
    recent = kline_data[-period:]
    total = sum(item.close_p for item in recent)
    return round(total / period, 2)


def calc_all_ma(kline_data: list[KlineItem]) -> dict:
    """计算5/10/20日均线，返回 {'ma5': xx, 'ma10': xx, 'ma20': xx}"""
    return {
        "ma5": calc_ma(kline_data, 5),
        "ma10": calc_ma(kline_data, 10),
        "ma20": calc_ma(kline_data, 20),
    }


def calc_daily_change(kline_data: list[KlineItem]) -> Optional[float]:
    """计算最新一日的涨跌幅(%)"""
    if len(kline_data) < 2:
        return None
    latest = kline_data[-1]
    if latest.change_pct != 0:
        return round(latest.change_pct, 2)
    # 如果change_pct没算出来，自己算
    prev_close = kline_data[-2].close_p
    if prev_close == 0:
        return None
    return round((latest.close_p - prev_close) / prev_close * 100, 2)


def calc_recent_changes(kline_data: list[KlineItem], n_days: int = 5) -> list[float]:
    """计算最近n天的涨跌幅列表"""
    changes = []
    for i in range(max(1, len(kline_data) - n_days), len(kline_data)):
        if kline_data[i].change_pct != 0:
            changes.append(kline_data[i].change_pct)
        elif kline_data[i-1].close_p != 0:
            c = (kline_data[i].close_p - kline_data[i-1].close_p) / kline_data[i-1].close_p * 100
            changes.append(round(c, 2))
    return changes


def calc_volatility(kline_data: list[KlineItem], period: int = 20) -> Optional[float]:
    """
    计算20日波动率（基于日收益率的标准差）
    返回百分比值
    """
    changes = calc_recent_changes(kline_data, period)
    if len(changes) < 2:
        return None

    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / len(changes)
    import math
    return round(math.sqrt(variance), 2)


def calc_current_change(quote: StockQuote) -> float:
    """计算当前实时涨跌幅"""
    return quote.change_pct


def calc_volume_ratio(kline_data: list[KlineItem]) -> Optional[float]:
    """
    计算量比 = 当日成交量 / 前5日均量
    """
    if len(kline_data) < 6:
        return None
    latest_vol = kline_data[-1].volume
    avg_vol = sum(item.volume for item in kline_data[-6:-1]) / 5
    if avg_vol == 0:
        return None
    return round(latest_vol / avg_vol, 2)


def calc_support_resistance(kline_data: list[KlineItem]) -> dict:
    """
    简单支撑位/阻力位计算
    支撑位 = 最近20日最低价
    阻力位 = 最近20日最高价
    """
    if not kline_data:
        return {"support": 0, "resistance": 0}
    recent = kline_data[-min(20, len(kline_data)):]
    low = min(item.low_p for item in recent)
    high = max(item.high_p for item in recent)
    return {"support": round(low, 2), "resistance": round(high, 2)}


def calc_is_gap_up(kline_data: list[KlineItem]) -> bool:
    """检测最新日是否跳空高开"""
    if len(kline_data) < 2:
        return False
    return kline_data[-1].low_p > kline_data[-2].high_p


def calc_is_gap_down(kline_data: list[KlineItem]) -> bool:
    """检测最新日是否跳空低开"""
    if len(kline_data) < 2:
        return False
    return kline_data[-1].high_p < kline_data[-2].low_p


def calc_ma_trend(kline_data: list[KlineItem]) -> str:
    """
    均线趋势判断
    :return: "多头排列" / "空头排列" / "交叉" / "不明"
    """
    ma5 = calc_ma(kline_data, 5)
    ma10 = calc_ma(kline_data, 10)
    ma20 = calc_ma(kline_data, 20)
    if ma5 is None or ma10 is None or ma20 is None:
        return "不明"
    if ma5 > ma10 > ma20:
        return "多头排列"
    elif ma5 < ma10 < ma20:
        return "空头排列"
    else:
        return "交叉整理"
