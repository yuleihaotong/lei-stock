"""fetcher 的字段映射测试。

东方财富的 f-字段语义是靠位置记的，错一位就全错（2026-10 重构时就发现
`change` 实际拿的是「最高价」）。这里用真实响应快照钉死映射关系，
断网也能跑。
"""

import json
import pathlib

import pytest

import fetcher

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_quote_maps_every_field(monkeypatch):
    payload = load("quote_600519.json")
    d = payload["data"]
    monkeypatch.setattr(fetcher.requests, "get", lambda *a, **k: FakeResponse(payload))

    q = fetcher.fetch_quote("600519")

    assert q is not None
    assert q.code == d["f57"]
    assert q.name == d["f58"]
    assert q.price == pytest.approx(d["f43"])
    assert q.change == pytest.approx(d["f169"]), "涨跌额取 f169，不是 f44(最高)"
    assert q.change_pct == pytest.approx(d["f170"]), "涨跌幅取 f170，不是 f45(最低)"
    assert q.high == pytest.approx(d["f44"])
    assert q.low == pytest.approx(d["f45"])
    assert q.open_p == pytest.approx(d["f46"])
    assert q.pre_close == pytest.approx(d["f60"]), "昨收取 f60，不是 f47(成交量)"
    assert q.volume == pytest.approx(d["f47"]), "成交量单位是手，不应缩放"
    assert q.amount == pytest.approx(d["f48"])
    assert q.turnover_rate == pytest.approx(d["f168"])


def test_amplitude_is_derived(monkeypatch):
    payload = load("quote_600519.json")
    d = payload["data"]
    monkeypatch.setattr(fetcher.requests, "get", lambda *a, **k: FakeResponse(payload))

    q = fetcher.fetch_quote("600519")

    expected = (d["f44"] - d["f45"]) / d["f60"] * 100
    assert q.amplitude == pytest.approx(expected, abs=0.01)


def test_quote_returns_none_on_empty_data(monkeypatch):
    monkeypatch.setattr(
        fetcher.requests, "get", lambda *a, **k: FakeResponse({"data": None})
    )
    assert fetcher.fetch_quote("600519") is None


def test_kline_parses_bars_and_keeps_volume_unit(monkeypatch):
    payload = load("kline_600519.json")
    lines = payload["data"]["klines"]
    monkeypatch.setattr(fetcher.requests, "get", lambda *a, **k: FakeResponse(payload))

    bars = fetcher.fetch_kline("600519", 30)

    assert len(bars) == 30
    first = lines[-30].split(",")
    last = lines[-1].split(",")
    assert bars[0].date == first[0]
    assert bars[-1].date == last[0]
    assert bars[-1].close_p == pytest.approx(float(last[2]))
    assert bars[-1].volume == pytest.approx(float(last[5])), "成交量是手，不除以 100"


def test_kline_change_pct_is_computed_from_previous_close(monkeypatch):
    payload = load("kline_600519.json")
    monkeypatch.setattr(fetcher.requests, "get", lambda *a, **k: FakeResponse(payload))

    bars = fetcher.fetch_kline("600519", 30)
    prev, cur = bars[-2], bars[-1]

    expected = (cur.close_p - prev.close_p) / prev.close_p * 100
    assert cur.change_pct == pytest.approx(expected, rel=1e-6)
