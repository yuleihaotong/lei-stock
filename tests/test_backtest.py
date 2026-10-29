"""回测器的正确性测试。

三条底线，任何一条破了回测就是自欺：
1. 不看未来（第 i 天只能用 i 及之前的数据）
2. 买卖价口径固定（次日开盘买、N 日后收盘卖）
3. 分组统计不把空样本算成 0 收益
"""

import pytest

from backtest import WARMUP, buy_and_hold, by_lamps, describe, evaluate_day, run
from fetcher import KlineItem


def series(closes):
    out = []
    for i, c in enumerate(closes):
        o = closes[i - 1] if i else c
        out.append(
            KlineItem(
                date=f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                open_p=o,
                close_p=c,
                high_p=max(o, c),
                low_p=min(o, c),
                volume=1000 + i,
                amount=(1000 + i) * c,
            )
        )
    return out


def test_trade_uses_next_open_and_horizon_close():
    # 构造 60 天，价格线性上涨；取第一个信号日核对买卖价
    bars = series([10 + 0.1 * i for i in range(60)])
    trades = run("600519", bars, horizons=(1,), warmup=WARMUP)

    assert trades, "应该有信号"
    first = trades[0]
    assert first.entry_date == bars[WARMUP + 1].date
    assert first.entry_price == pytest.approx(bars[WARMUP + 1].open_p)
    assert first.exit_date == bars[WARMUP + 1].date  # horizon=1 → 当日收盘卖
    assert first.exit_price == pytest.approx(bars[WARMUP + 1].close_p)
    assert first.ret_pct == pytest.approx(
        (bars[WARMUP + 1].close_p / bars[WARMUP + 1].open_p - 1) * 100
    )


def test_no_lookahead():
    """把未来的 K 线换成暴涨暴跌，同一个信号日的四灯结果不能变。"""
    base = [10 + 0.1 * i for i in range(60)]
    bars = series(base)
    i = 40

    normal = evaluate_day("600519", bars, i)

    tampered = series(base[: i + 1] + [999.0, 1.0, 999.0])
    after = evaluate_day("600519", tampered, i)

    assert (normal.qujian, normal.zoushi, normal.bankuai, normal.liangjia) == (
        after.qujian, after.zoushi, after.bankuai, after.liangjia,
    )


def test_trades_never_exceed_available_bars():
    bars = series([10 + 0.1 * i for i in range(50)])
    trades = run("600519", bars, horizons=(1, 3, 5), warmup=WARMUP)
    dates = [b.date for b in bars]

    for trade in trades:
        assert trade.signal_date in dates
        assert trade.entry_date in dates
        assert trade.exit_date in dates
        assert dates.index(trade.exit_date) > dates.index(trade.signal_date)


def test_describe_handles_empty_and_values():
    assert describe([]) is None

    stat = describe([1.0, -1.0, 2.0, 0.5])
    assert stat["n"] == 4
    assert stat["win"] == pytest.approx(75.0)
    assert stat["worst"] == pytest.approx(-1.0)
    assert stat["best"] == pytest.approx(2.0)


def test_by_lamps_buckets_by_red_count():
    bars = series([10 + 0.1 * i for i in range(60)])
    trades = run("600519", bars, horizons=(1,), warmup=WARMUP)

    buckets = by_lamps(trades, horizon=1)
    assert buckets, "至少有一个灯数分桶"
    assert all(0 <= lamps <= 4 for lamps in buckets)
    assert sum(stat["n"] for stat in buckets.values()) == len(trades)


def test_buy_and_hold_matches_definition():
    bars = series([10 + 0.1 * i for i in range(60)])
    expected = (bars[-1].close_p / bars[WARMUP].open_p - 1) * 100
    assert buy_and_hold(bars) == pytest.approx(expected)


def test_cost_is_subtracted_from_every_trade():
    bars = series([10 + 0.1 * i for i in range(60)])
    gross = run("600519", bars, horizons=(1,), warmup=WARMUP)
    net = run("600519", bars, horizons=(1,), warmup=WARMUP, cost_pct=0.15)

    assert len(gross) == len(net)
    assert net[0].ret_pct == pytest.approx(gross[0].ret_pct - 0.15)
    assert net[-1].ret_pct == pytest.approx(gross[-1].ret_pct - 0.15)


def test_custom_signal_replaces_four_lamps():
    bars = series([10 + 0.1 * i for i in range(60)])
    calls = []

    def always_two(code, day_bars, i):
        calls.append(i)
        return 2

    trades = run("600519", bars, horizons=(1,), warmup=WARMUP, signal=always_two)

    assert calls, "信号函数应该被逐日调用"
    assert all(t.lamps == 2 for t in trades)
    assert len(trades) == len(set(calls)), "每个信号日只应产生一笔 1 日交易"
