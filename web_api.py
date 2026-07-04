"""
web_api.py - Flask API服务（APK模式专用）
在Android APK中作为后台服务运行，提供REST API给WebView前端调用
"""

import json
import time
import threading
from typing import Optional

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    # 降级方案：用Python内置HTTP服务器
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

from fetcher import (
    fetch_market_overview, fetch_quote, fetch_kline,
    fetch_quotes_batch, search_stocks, StockQuote, KlineItem
)
from analyzer import calc_all_ma, calc_volatility, calc_daily_change
from indicator_engine import analyze, FourLampResult, analyze_batch
from database import (
    init_db, get_watchlist, add_watchlist, remove_watchlist, is_in_watchlist,
    get_search_history, add_search_history, get_refresh_interval,
    set_refresh_interval, update_watchlist_name
)
from scheduler import get_scheduler

# ─── 数据序列化 ──────────────────────────────────────────────────────

def quote_to_dict(q: Optional[StockQuote]) -> dict:
    if q is None:
        return {}
    return {
        "code": q.code,
        "name": q.name,
        "price": q.price,
        "change": q.change,
        "change_pct": q.change_pct,
        "high": q.high,
        "low": q.low,
        "open": q.open_p,
        "pre_close": q.pre_close,
        "volume": q.volume,
        "amount": q.amount,
        "turnover_rate": q.turnover_rate,
        "amplitude": q.amplitude,
        "pe": q.pe,
        "pb": q.pb,
        "market": q.market,
    }


def kline_to_dict(kline: list[KlineItem]) -> list[dict]:
    return [
        {
            "date": k.date,
            "open": k.open_p,
            "close": k.close_p,
            "high": k.high_p,
            "low": k.low_p,
            "volume": k.volume,
            "amount": k.amount,
            "change_pct": k.change_pct,
        }
        for k in kline
    ]


def lamp_to_dict(result: FourLampResult) -> dict:
    return {
        "code": result.code,
        "name": result.name,
        "qujian": result.qujian,
        "zoushi": result.zoushi,
        "bankuai": result.bankuai,
        "liangjia": result.liangjia,
        "red_count": result.red_count,
        "all_red": result.all_red,
        "any_green": result.any_green,
        "signal": result.signal,
    }


def serialize_error(msg: str) -> dict:
    return {"error": msg}


# ─── Flask API 实现 ─────────────────────────────────────────────────

class StockAPI:
    """股票API服务"""

    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self._server = None
        self._thread = None

    def _create_flask_app(self):
        """创建Flask应用"""
        if not FLASK_AVAILABLE:
            return None

        app = Flask(__name__)
        CORS(app)

        @app.route("/api/market", methods=["GET"])
        def api_market():
            try:
                mo = fetch_market_overview()
                return jsonify({
                    "sh_name": mo.sh_name,
                    "sh_code": mo.sh_code,
                    "sh_price": mo.sh_price,
                    "sh_change": mo.sh_change,
                    "sh_change_pct": mo.sh_change_pct,
                    "sz_name": mo.sz_name,
                    "sz_code": mo.sz_code,
                    "sz_price": mo.sz_price,
                    "sz_change": mo.sz_change,
                    "sz_change_pct": mo.sz_change_pct,
                    "cy_name": mo.cy_name,
                    "cy_code": mo.cy_code,
                    "cy_price": mo.cy_price,
                    "cy_change": mo.cy_change,
                    "cy_change_pct": mo.cy_change_pct,
                })
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/quote", methods=["GET"])
        def api_quote():
            code = request.args.get("code", "")
            if not code:
                return jsonify(serialize_error("缺少code参数")), 400
            try:
                q = fetch_quote(code)
                return jsonify(quote_to_dict(q))
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/search", methods=["GET"])
        def api_search():
            keyword = request.args.get("keyword", "")
            if not keyword:
                return jsonify([])
            try:
                results = search_stocks(keyword)
                return jsonify(results)
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/kline", methods=["GET"])
        def api_kline():
            code = request.args.get("code", "")
            days = request.args.get("days", 30, type=int)
            if not code:
                return jsonify(serialize_error("缺少code参数")), 400
            try:
                kline = fetch_kline(code, days)
                return jsonify(kline_to_dict(kline))
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/analyze", methods=["GET"])
        def api_analyze():
            code = request.args.get("code", "")
            if not code:
                return jsonify(serialize_error("缺少code参数")), 400
            try:
                kline = fetch_kline(code, 30)
                quote = fetch_quote(code)
                result = analyze(code, kline, quote)
                return jsonify(lamp_to_dict(result))
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/detail", methods=["GET"])
        def api_detail():
            """综合详情：行情+K线+分析+指标"""
            code = request.args.get("code", "")
            if not code:
                return jsonify(serialize_error("缺少code参数")), 400
            try:
                quote = fetch_quote(code)
                kline = fetch_kline(code, 30)
                result = analyze(code, kline, quote)
                ma_data = calc_all_ma(kline)
                vol20 = calc_volatility(kline, 20)
                daily_chg = calc_daily_change(kline)

                return jsonify({
                    "quote": quote_to_dict(quote),
                    "kline": kline_to_dict(kline),
                    "lamp": lamp_to_dict(result),
                    "indicators": {
                        "ma5": ma_data.get("ma5"),
                        "ma10": ma_data.get("ma10"),
                        "ma20": ma_data.get("ma20"),
                        "volatility_20": vol20,
                        "daily_change": daily_chg,
                    },
                })
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/watchlist", methods=["GET"])
        def api_get_watchlist():
            try:
                items = get_watchlist()
                # 批量获取行情
                codes = [item["code"] for item in items]
                quotes = fetch_quotes_batch(codes)
                results = analyze_batch(codes)

                output = []
                for idx, item in enumerate(items):
                    output.append({
                        "code": item["code"],
                        "name": item["name"],
                        "added_at": item["added_at"],
                        "quote": quote_to_dict(quotes[idx]) if idx < len(quotes) else {},
                        "lamp": lamp_to_dict(results[idx]) if idx < len(results) else {},
                    })
                return jsonify(output)
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/watchlist/add", methods=["POST"])
        def api_add_watchlist():
            data = request.get_json(force=True, silent=True) or request.form
            code = data.get("code", "")
            name = data.get("name", "")
            if not code:
                return jsonify(serialize_error("缺少code参数")), 400
            try:
                ok = add_watchlist(code, name)
                return jsonify({"success": ok, "code": code})
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/watchlist/remove", methods=["POST"])
        def api_remove_watchlist():
            data = request.get_json(force=True, silent=True) or request.form
            code = data.get("code", "")
            if not code:
                return jsonify(serialize_error("缺少code参数")), 400
            try:
                ok = remove_watchlist(code)
                return jsonify({"success": ok, "code": code})
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/watchlist/check", methods=["GET"])
        def api_check_watchlist():
            code = request.args.get("code", "")
            if not code:
                return jsonify(serialize_error("缺少code参数")), 400
            try:
                return jsonify({"in_watchlist": is_in_watchlist(code)})
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/settings", methods=["GET"])
        def api_get_settings():
            try:
                return jsonify({
                    "refresh_interval": get_refresh_interval(),
                })
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/settings/interval", methods=["POST"])
        def api_set_interval():
            data = request.get_json(force=True, silent=True) or request.form
            interval = data.get("interval", 60, type=int)
            try:
                set_refresh_interval(interval)
                s = get_scheduler()
                s.set_interval(interval)
                return jsonify({"success": True, "interval": interval})
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/search/history", methods=["GET"])
        def api_search_history():
            try:
                return jsonify(get_search_history(10))
            except Exception as e:
                return jsonify(serialize_error(str(e))), 500

        @app.route("/api/health", methods=["GET"])
        def api_health():
            return jsonify({"status": "ok", "service": "stock_tool"})

        return app

    def start(self, daemon=True):
        """启动API服务"""
        app = self._create_flask_app()
        if app:
            self._thread = threading.Thread(
                target=lambda: app.run(
                    host=self.host, port=self.port,
                    debug=False, use_reloader=False
                ),
                daemon=daemon,
                name="StockAPI"
            )
            self._thread.start()
            print(f"[web_api] Flask服务启动: http://{self.host}:{self.port}")
            return True
        else:
            print("[web_api] Flask不可用，使用内置HTTP服务器")
            return self._start_simple_http()

    def _start_simple_http(self):
        """降级方案：简易HTTP服务器"""
        # 简易实现只返回静态提示
        import http.server

        class SimpleHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Flask未安装，请执行: pip install flask flask-cors"
                }).encode())

            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Flask未安装"}).encode())

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

        self._server = HTTPServer((self.host, self.port), SimpleHandler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="StockAPISimple"
        )
        self._thread.start()
        print(f"[web_api] 简易HTTP服务启动: http://{self.host}:{self.port}")
        return True

    def stop(self):
        if self._server:
            self._server.shutdown()
        print("[web_api] 服务已停止")


# 全局API服务实例
_api_service: Optional[StockAPI] = None


def start_api(host="127.0.0.1", port=5000):
    """启动全局API服务"""
    global _api_service
    if _api_service is None:
        _api_service = StockAPI(host, port)
    _api_service.start()
    return _api_service


def stop_api():
    """停止全局API服务"""
    global _api_service
    if _api_service:
        _api_service.stop()
        _api_service = None
