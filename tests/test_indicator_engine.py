"""四灯规则的判断测试。

这里只断言「方向性」结论（强势该红、单边下跌该绿），不锁死具体阈值——
阈值以后要调，方向不该调。所有数据都是构造的，不联网。
"""

import pytest

from fetcher import KlineItem, StockQuote
from indicator_engine import analyze, judge_bankuai, judge_liangjia, judge_qujian, judge_zoushi


def series(closes, volumes=None, opens=None):
    """按收盘价序列构造 K线，开盘价默认等于前一日收盘。"""
    volumes = volumes or [1000] * len(closes)
    out = []
    for i, c in enumerate(closes):
        o = opens[i] if opens else (closes[i - 1] if i else c)
        out.append(
            KlineItem(
                date=f"2026-01-{i + 1:02d}",
                open_p=o,
                close_p=c,
                high_p=max(o, c),
                low_p=min(o, c),
                volume=volumes[i],
                amount=volumes[i] * c,
            )
        )
    return out


def quote(price, pre_close):
    return StockQuote(
        code="600519",
        name="贵州茅台",
        price=price,
        change=price - pre_close,
        change_pct=(price - pre_close) / pre_close * 100,
        high=price,
        low=price,
        open_p=pre_close,
        pre_close=pre_close,
        volume=1000,
        amount=1.0,
    )


UP = [10 + i * 0.5 for i in range(30)]          # 单边上涨
DOWN = [30 - i * 0.5 for i in range(30)]        # 单边下跌


def test_uptrend_lights_qujian_and_zoushi():
    bars = series(UP)
    assert judge_qujian(bars, quote(bars[-1].close_p, bars[-2].close_p)) is True
    assert judge_zoushi(bars) is True


def test_downtrend_leaves_every_lamp_green():
    bars = series(DOWN)
    # 阴线 + 缩量的组合本来可能点亮量价灯，这里给放量阴线，确保四灯全绿
    bars = series(DOWN, volumes=[1000] * 28 + [5000, 6000])
    q = quote(bars[-1].close_p, bars[-2].close_p)

    assert judge_qujian(bars, q) is False
    assert judge_zoushi(bars) is False
    assert judge_liangjia(bars, q) is False


def test_short_series_never_lights():
    bars = series([10, 11, 12])
    assert judge_qujian(bars) is False
    assert judge_zoushi(bars) is False
    assert judge_bankuai("600519", bars) is False
    assert judge_liangjia(bars) is False


def test_analyze_reports_stock_name_not_date():
    bars = series(UP)
    q = quote(bars[-1].close_p, bars[-2].close_p)

    result = analyze("600519", bars, q)

    assert result.code == "600519"
    assert result.name == "贵州茅台", "四灯结果里的 name 应该是股票名，不是最后一根K线的日期"


def test_analyze_without_quote_still_works():
    bars = series(UP)
    result = analyze("600519", bars, quote(bars[-1].close_p, bars[-2].close_p))
    assert set(vars(result)) >= {"qujian", "zoushi", "bankuai", "liangjia"}
    assert isinstance(result.signal, str) and result.signal


def test_red_count_matches_lamps():
    bars = series(UP)
    q = quote(bars[-1].close_p, bars[-2].close_p)
    result = analyze("600519", bars, q)
    lamps = [result.qujian, result.zoushi, result.bankuai, result.liangjia]
    assert result.red_count == sum(1 for lamp in lamps if lamp)
