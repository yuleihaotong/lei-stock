"""backtest.py —— 四灯策略的历史回测。

回答一个具体问题：**历史上四灯亮起之后买入，接下来 N 天到底赚不赚、赚多少、亏多少。**

约定（写死在代码里，避免口径漂移）：

* **不看未来**：第 i 天只用 `bars[:i+1]`，指标函数全是向后看的切片。
* **信号在收盘产生，次日开盘买入**（`bars[i+1].open_p`），
  持有 N 天后在 `bars[i+N].close_p` 卖出。
* 收益已含买卖价差，**不含**手续费、印花税、滑点。真实收益要再减约 0.1%–0.2%。
* 所有分桶按"当天的红灯数"（0–4）统计，和 UI 里的四灯一一对应。

用法：

    python backtest.py 600519 000001 300750
    python backtest.py --universe --years 3 --out reports/backtest.md
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from fetcher import KlineItem, StockQuote, fetch_kline
from indicator_engine import FourLampResult, analyze

WARMUP = 25          # 20 日均线 + 余量
HORIZONS = (1, 3, 5)
DEFAULT_UNIVERSE = [
    "600519",  # 贵州茅台
    "000001",  # 平安银行
    "600036",  # 招商银行
    "300750",  # 宁德时代
    "002594",  # 比亚迪
    "601318",  # 中国平安
    "600900",  # 长江电力
    "000858",  # 五粮液
    "601899",  # 紫金矿业
    "002415",  # 海康威视
]


@dataclass
class Trade:
    code: str
    signal_date: str
    lamps: int
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    horizon: int
    ret_pct: float


def synthetic_quote(code: str, bars: list[KlineItem], i: int) -> StockQuote:
    """把第 i 根 K 线包装成 quote，避免回测时去打实时接口。"""
    bar = bars[i]
    prev = bars[i - 1].close_p if i > 0 else bar.close_p
    change_pct = (bar.close_p - prev) / prev * 100 if prev else 0.0
    return StockQuote(
        code=code,
        name="",
        price=bar.close_p,
        change=bar.close_p - prev,
        change_pct=change_pct,
        high=bar.high_p,
        low=bar.low_p,
        open_p=bar.open_p,
        pre_close=prev,
        volume=bar.volume,
        amount=bar.amount,
    )


def evaluate_day(code: str, bars: list[KlineItem], i: int) -> FourLampResult:
    """对第 i 天做四灯判断，只用 i 之前（含 i）的数据。"""
    return analyze(code, bars[: i + 1], synthetic_quote(code, bars, i))


def run(
    code: str,
    bars: list[KlineItem],
    horizons: tuple[int, ...] = HORIZONS,
    warmup: int = WARMUP,
) -> list[Trade]:
    """逐日回测一只股票，返回所有可成交的信号。"""
    trades: list[Trade] = []
    n = len(bars)
    for i in range(warmup, n - 1):
        result = evaluate_day(code, bars, i)
        lights = result.red_count
        for horizon in horizons:
            j = i + horizon
            if j >= n:
                continue
            entry = bars[i + 1].open_p
            exit_price = bars[j].close_p
            if entry <= 0:
                continue
            trades.append(
                Trade(
                    code=code,
                    signal_date=bars[i].date,
                    lamps=lights,
                    entry_date=bars[i + 1].date,
                    entry_price=entry,
                    exit_date=bars[j].date,
                    exit_price=exit_price,
                    horizon=horizon,
                    ret_pct=(exit_price / entry - 1) * 100,
                )
            )
    return trades


def describe(returns: list[float]) -> dict | None:
    """一组收益的描述统计。空样本返回 None，而不是 0。"""
    if not returns:
        return None
    ordered = sorted(returns)
    n = len(ordered)
    mean = statistics.fmean(ordered)
    # t 值：均值相对标准误。|t| < 2 基本可以认为和 0 没区别。
    t_stat = None
    if n > 1:
        sd = statistics.stdev(ordered)
        if sd > 0:
            t_stat = mean / (sd / n**0.5)
    return {
        "n": n,
        "mean": mean,
        "median": statistics.median(ordered),
        "win": sum(1 for r in ordered if r > 0) / n * 100,
        "p10": ordered[max(0, int(0.10 * (n - 1)))],
        "p90": ordered[min(n - 1, int(0.90 * (n - 1)))],
        "worst": ordered[0],
        "best": ordered[-1],
        "t": t_stat,
    }


def by_lamps(trades: list[Trade], horizon: int) -> dict[int, dict]:
    buckets: dict[int, list[float]] = {}
    for trade in trades:
        if trade.horizon != horizon:
            continue
        buckets.setdefault(trade.lamps, []).append(trade.ret_pct)
    return {lamps: describe(rets) for lamps, rets in sorted(buckets.items())}


def buy_and_hold(bars: list[KlineItem], warmup: int = WARMUP) -> float:
    """同期买入持有的基准收益（同样从 warmup 之后算）。"""
    if len(bars) <= warmup + 1:
        return 0.0
    entry = bars[warmup].open_p
    exit_price = bars[-1].close_p
    if entry <= 0:
        return 0.0
    return (exit_price / entry - 1) * 100


def markdown_report(per_code: dict[str, list[Trade]], baselines: dict[str, float],
                    days: int) -> str:
    lines: list[str] = []
    lines.append("# 四灯策略回测报告\n")
    lines.append(
        f"- 样本：{len(per_code)} 只股票，每只最近 {days} 个交易日\n"
        f"- 口径：信号日收盘 → 次日开盘买入 → 持有 N 日收盘卖出\n"
        f"- 未计手续费/印花税/滑点（实际再加 0.1%–0.2% 成本）\n"
    )

    for horizon in HORIZONS:
        lines.append(f"\n## 持有 {horizon} 日\n")
        lines.append("| 红灯数 | 样本 | 胜率 | 平均 | 中位 | P10 | P90 | 最差 | 最好 | t |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        all_trades = [t for ts in per_code.values() for t in ts]
        for lamps, stat in by_lamps(all_trades, horizon).items():
            if not stat:
                continue
            t_text = "—" if stat["t"] is None else f"{stat['t']:.2f}"
            lines.append(
                f"| {lamps} | {stat['n']} | {stat['win']:.1f}% | {stat['mean']:+.2f}% | "
                f"{stat['median']:+.2f}% | {stat['p10']:+.2f}% | {stat['p90']:+.2f}% | "
                f"{stat['worst']:+.2f}% | {stat['best']:+.2f}% | {t_text} |"
            )

    lines.append("\n## 同期买入持有基准\n")
    lines.append("| 股票 | 基准收益 |")
    lines.append("|---|---:|")
    for code, ret in sorted(baselines.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"| {code} | {ret:+.2f}% |")

    lines.append(
        "\n## 怎么读这份报告\n"
        "\n"
        "1. **t 值是关键**。|t| < 2 说明这批样本的均值跟 0 没有统计差别，"
        "看到 +0.06% 就兴奋是自欺。\n"
        "2. **15 个组合挑最好的会骗人**。4 个灯数 × 3 个期限 = 15 个假设，"
        "其中冒出一两个 t > 3 属于正常，必须在**样本外**（别的时段、别的股票池）复现才算数。\n"
        "3. **成本没算**。双边约 0.1%–0.2%，任何期望收益低于这个数的桶，实盘都是负的。\n"
        "4. **样本偏差**：内置 10 只是知名股，不代表全市场；500 天 ≈ 2 年，只覆盖一种市场状态。\n"
    )

    return "\n".join(lines) + "\n"


def write_csv(trades: list[Trade], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["code", "signal_date", "lamps", "entry_date", "entry_price",
             "exit_date", "exit_price", "horizon", "ret_pct"]
        )
        for t in trades:
            writer.writerow(
                [t.code, t.signal_date, t.lamps, t.entry_date, f"{t.entry_price:.2f}",
                 t.exit_date, f"{t.exit_price:.2f}", t.horizon, f"{t.ret_pct:.4f}"]
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="四灯策略回测")
    parser.add_argument("codes", nargs="*", help="股票代码；留空则用内置样本池")
    parser.add_argument("--universe", action="store_true", help="跑内置的 10 只样本")
    parser.add_argument("--days", type=int, default=500, help="每只股票取多少个交易日")
    parser.add_argument("--out", type=str, default="reports/backtest.md")
    parser.add_argument("--csv", type=str, default="reports/trades.csv")
    args = parser.parse_args(argv)

    codes = args.codes or (DEFAULT_UNIVERSE if args.universe or not args.codes else [])
    if not codes:
        parser.error("没有指定股票代码")

    per_code: dict[str, list[Trade]] = {}
    baselines: dict[str, float] = {}
    all_trades: list[Trade] = []

    for code in codes:
        bars = fetch_kline(code, days=max(args.days, 60))
        if len(bars) < WARMUP + 10:
            print(f"[skip] {code}: 只有 {len(bars)} 根 K 线，样本不足", file=sys.stderr)
            continue
        trades = run(code, bars)
        per_code[code] = trades
        all_trades.extend(trades)
        baselines[code] = buy_and_hold(bars)
        print(f"{code}: {len(bars)} 根K线, {len(trades)} 笔交易", file=sys.stderr)

    if not per_code:
        print("没有可用样本", file=sys.stderr)
        return 1

    report = markdown_report(per_code, baselines, args.days)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    write_csv(all_trades, Path(args.csv))

    print(f"\n报告: {out}\n明细: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
