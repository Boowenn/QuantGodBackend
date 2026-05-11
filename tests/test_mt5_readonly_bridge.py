import argparse
import importlib.util
import json
import os
import tempfile
import time
import unittest
from collections import namedtuple
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "mt5_readonly_bridge.py"
SPEC = importlib.util.spec_from_file_location("mt5_readonly_bridge", MODULE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bridge)


TerminalInfo = namedtuple(
    "TerminalInfo",
    "connected trade_allowed dlls_allowed name company path data_path commondata_path codepage maxbars",
)
AccountInfo = namedtuple(
    "AccountInfo",
    "login server name currency company balance equity profit margin margin_free margin_level leverage trade_allowed trade_expert",
)
PositionInfo = namedtuple(
    "PositionInfo",
    "ticket identifier symbol type volume price_open price_current sl tp profit swap magic comment time",
)
OrderInfo = namedtuple(
    "OrderInfo",
    "ticket symbol type volume_initial volume_current price_open price_current sl tp magic comment time_setup",
)
SymbolInfo = namedtuple(
    "SymbolInfo",
    "name description path visible select currency_base currency_profit digits point spread trade_mode volume_min volume_max volume_step",
)
TickInfo = namedtuple("TickInfo", "bid ask last volume time")


class FakeMt5:
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2

    def __init__(self):
        self.calls = []

    def terminal_info(self):
        self.calls.append("terminal_info")
        return TerminalInfo(
            True,
            True,
            False,
            "Fake HFM MT5",
            "Fake Broker",
            "C:\\MT5",
            "C:\\MT5",
            "C:\\Common",
            65001,
            100000,
        )

    def account_info(self):
        self.calls.append("account_info")
        return AccountInfo(
            123456,
            "Fake-Live",
            "Read Only",
            "USC",
            "Fake Broker",
            10000.0,
            10025.0,
            25.0,
            1.0,
            10024.0,
            1002400.0,
            1000,
            True,
            True,
        )

    def positions_get(self, symbol=None):
        self.calls.append(("positions_get", symbol or ""))
        return [
            PositionInfo(
                1001,
                1001,
                symbol or "EURUSDc",
                self.POSITION_TYPE_BUY,
                0.01,
                1.10001,
                1.10021,
                1.09,
                1.12,
                2.0,
                0.0,
                520001,
                "fake position",
                1777389974,
            )
        ]

    def orders_get(self, symbol=None):
        self.calls.append(("orders_get", symbol or ""))
        return [
            OrderInfo(
                2001,
                symbol or "EURUSDc",
                self.ORDER_TYPE_BUY_LIMIT,
                0.01,
                0.01,
                1.099,
                0.0,
                1.09,
                1.12,
                520001,
                "fake order",
                1777389000,
            )
        ]

    def symbols_get(self, group="*"):
        self.calls.append(("symbols_get", group))
        return [
            SymbolInfo(
                "EURUSDc",
                "Euro vs US Dollar (Cent)",
                "ForexCent\\EURUSDc",
                True,
                True,
                "EUR",
                "USD",
                5,
                0.00001,
                17,
                4,
                0.01,
                200.0,
                0.01,
            )
        ]

    def symbol_info(self, symbol):
        self.calls.append(("symbol_info", symbol))
        return SymbolInfo(
            symbol,
            "Euro vs US Dollar (Cent)",
            f"ForexCent\\{symbol}",
            True,
            True,
            "EUR",
            "USD",
            5,
            0.00001,
            17,
            4,
            0.01,
            200.0,
            0.01,
        )

    def symbol_info_tick(self, symbol):
        self.calls.append(("symbol_info_tick", symbol))
        return TickInfo(1.1002, 1.10037, 1.1003, 100, 1777389999)

    def last_error(self):
        return (1, "Success")


class Mt5ReadOnlyBridgeTests(unittest.TestCase):
    def test_safety_metadata_disallows_mutation(self):
        self.assertTrue(bridge.SAFETY["readOnly"])
        self.assertFalse(bridge.SAFETY["orderSendAllowed"])
        self.assertFalse(bridge.SAFETY["closeAllowed"])
        self.assertFalse(bridge.SAFETY["cancelAllowed"])
        self.assertFalse(bridge.SAFETY["credentialStorageAllowed"])
        self.assertFalse(bridge.SAFETY["livePresetMutationAllowed"])
        self.assertFalse(bridge.SAFETY["mutatesMt5"])

    def test_parse_args_defaults_to_snapshot(self):
        args = bridge.parse_args([])
        self.assertEqual(args.endpoint, "snapshot")
        self.assertEqual(args.group, "*")
        self.assertEqual(args.limit, bridge.DEFAULT_SYMBOL_LIMIT)
        self.assertEqual(args.symbols_limit, bridge.DEFAULT_SYMBOL_LIMIT)

    def test_mutating_endpoint_names_are_not_registered(self):
        self.assertNotIn("order", bridge.ENDPOINTS)
        self.assertNotIn("close", bridge.ENDPOINTS)
        self.assertNotIn("cancel", bridge.ENDPOINTS)

    def test_public_error_keeps_read_only_safety(self):
        payload = bridge.public_error("offline", detail="missing package")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "UNAVAILABLE")
        self.assertEqual(payload["detail"], "missing package")
        self.assertEqual(payload["safety"], bridge.SAFETY)

    def test_symbol_filter_is_whitespace_only(self):
        self.assertEqual(bridge.normalize_symbol_filter("  EURUSDc  "), "EURUSDc")
        self.assertEqual(bridge.normalize_symbol_filter(None), "")

    def test_snapshot_contract_with_fake_mt5(self):
        fake = FakeMt5()
        args = bridge.parse_args(["--endpoint", "snapshot", "--symbol", "EURUSDc", "--symbols-limit", "20"])
        payload = bridge.build_endpoint_payload(fake, args)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "MT5_READONLY_BRIDGE_V1")
        self.assertEqual(payload["endpoint"], "snapshot")
        self.assertEqual(payload["status"], "CONNECTED")
        self.assertEqual(payload["safety"], bridge.SAFETY)
        self.assertFalse(payload["safety"]["orderSendAllowed"])
        self.assertFalse(payload["safety"]["closeAllowed"])
        self.assertFalse(payload["safety"]["cancelAllowed"])

        self.assertIn("terminal", payload)
        self.assertIn("account", payload)
        self.assertIn("positions", payload)
        self.assertIn("orders", payload)
        self.assertIn("symbols", payload)
        self.assertIn("quote", payload)
        self.assertEqual(payload["positions"]["items"][0]["symbol"], "EURUSDc")
        self.assertEqual(payload["orders"]["items"][0]["type"], "buy_limit")
        self.assertEqual(payload["symbols"]["items"][0]["name"], "EURUSDc")
        self.assertTrue(payload["quote"]["ok"])
        self.assertEqual(payload["quote"]["symbol"], "EURUSDc")

        called_names = {call[0] if isinstance(call, tuple) else call for call in fake.calls}
        self.assertNotIn("order_send", called_names)
        self.assertNotIn("symbol_select", called_names)
        self.assertNotIn("positions_close", called_names)

    def test_each_readonly_endpoint_contract_keeps_safety(self):
        fake = FakeMt5()
        for endpoint in sorted(bridge.ENDPOINTS):
            args = bridge.parse_args(["--endpoint", endpoint, "--symbol", "EURUSDc"])
            payload = bridge.build_endpoint_payload(fake, args)
            self.assertIn("generatedAtIso", payload)
            self.assertEqual(payload["safety"], bridge.SAFETY)
            self.assertFalse(payload["safety"]["orderSendAllowed"])
            self.assertFalse(payload["safety"]["closeAllowed"])
            self.assertFalse(payload["safety"]["cancelAllowed"])

    def test_ea_snapshot_fallback_reads_dashboard_without_mt5_python(self):
        dashboard = {
            "watchlist": "USDJPYc",
            "account": {
                "number": 186054398,
                "name": "Read Only",
                "server": "HFMarketsGlobal-Live12",
                "currency": "USC",
                "balance": 10003.02,
                "equity": 10003.02,
                "freeMargin": 10003.02,
                "leverage": 1000,
            },
            "runtime": {
                "terminalConnected": True,
                "accountTradeAllowed": True,
                "accountExpertTradeAllowed": True,
                "terminalTradeAllowed": True,
                "programTradeAllowed": True,
            },
            "market": {"symbol": "USDJPYc", "bid": 157.026, "ask": 157.091, "spread": 6.5},
            "symbols": [
                {
                    "symbol": "USDJPYc",
                    "status": "READY",
                    "bid": 157.026,
                    "ask": 157.091,
                    "spread": 6.5,
                    "tradeMode": "FULL",
                    "entryTradeAllowed": True,
                }
            ],
            "openTrades": [
                {
                    "ticket": 1001,
                    "positionId": 1001,
                    "type": "BUY",
                    "symbol": "USDJPYc",
                    "actualLots": 0.01,
                    "openPrice": 156.5,
                    "actualProfit": 0.25,
                    "comment": "QG_RSI_Rev_MT5_BUY",
                }
            ],
        }

        old_runtime = os.environ.get("QG_RUNTIME_DIR")
        with tempfile.TemporaryDirectory() as tmp_dir:
            Path(tmp_dir, "QuantGod_Dashboard.json").write_text(json.dumps(dashboard), encoding="utf-8")
            os.environ["QG_RUNTIME_DIR"] = tmp_dir
            try:
                args = bridge.parse_args(["--endpoint", "snapshot", "--symbol", "USDJPYc"])
                payload = bridge.build_ea_snapshot_fallback(args)
            finally:
                if old_runtime is None:
                    os.environ.pop("QG_RUNTIME_DIR", None)
                else:
                    os.environ["QG_RUNTIME_DIR"] = old_runtime

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "MT5_READONLY_BRIDGE_V1_EA_SNAPSHOT_FALLBACK")
        self.assertEqual(payload["status"], "EA_SNAPSHOT")
        self.assertEqual(payload["account"]["login"], 186054398)
        self.assertEqual(payload["positions"]["count"], 1)
        self.assertEqual(payload["positions"]["items"][0]["volume"], 0.01)
        self.assertTrue(payload["quote"]["ok"])
        self.assertEqual(payload["quote"]["bid"], 157.026)
        self.assertEqual(payload["symbols"]["items"][0]["tradeMode"], "FULL")
        self.assertFalse(payload["safety"]["orderSendAllowed"])

    def test_ea_snapshot_fallback_merges_standalone_usdjpy_rsi_diagnostics(self):
        dashboard = {
            "watchlist": "USDJPYc",
            "account": {"number": 186054398, "server": "HFMarketsGlobal-Live12", "currency": "USC"},
            "runtime": {"terminalConnected": True, "terminalTradeAllowed": True, "programTradeAllowed": True},
            "market": {"symbol": "USDJPYc", "bid": 156.24, "ask": 156.25, "tradeMode": "FULL"},
        }
        diagnostics = {
            "schema": "quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1",
            "symbol": "USDJPYc",
            "state": "READY_BUY_SIGNAL",
            "stateZh": "RSI 买入信号已触发，等待 EA 守门执行",
        }

        old_runtime = os.environ.get("QG_RUNTIME_DIR")
        with tempfile.TemporaryDirectory() as tmp_dir:
            Path(tmp_dir, "QuantGod_Dashboard.json").write_text(json.dumps(dashboard), encoding="utf-8")
            Path(tmp_dir, "QuantGod_USDJPYRsiEntryDiagnostics.json").write_text(
                json.dumps(diagnostics),
                encoding="utf-8",
            )
            os.environ["QG_RUNTIME_DIR"] = tmp_dir
            try:
                args = bridge.parse_args(["--endpoint", "snapshot", "--symbol", "USDJPYc"])
                payload = bridge.build_ea_snapshot_fallback(args)
            finally:
                if old_runtime is None:
                    os.environ.pop("QG_RUNTIME_DIR", None)
                else:
                    os.environ["QG_RUNTIME_DIR"] = old_runtime

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["usdJpyRsiEntryDiagnostics"]["state"], "READY_BUY_SIGNAL")
        self.assertEqual(payload["usdJpyRsiEntryDiagnostics"]["symbol"], "USDJPYc")
        self.assertEqual(payload["usdJpyRsiEntryDiagnosticsSource"]["type"], "standalone_file")

    def write_dashboard_with_trade_state(self, runtime: Path, mtime: float) -> Path:
        path = runtime / "QuantGod_Dashboard.json"
        path.write_text(
            json.dumps(
                {
                    "watchlist": "USDJPYc",
                    "runtime": {"tradeStatus": "READY", "terminalConnected": True},
                    "account": {"number": 123456, "server": "HFM", "currency": "USC", "balance": 10000},
                    "market": {"symbol": "USDJPYc", "bid": 157.01, "ask": 157.03},
                    "openTrades": [
                        {
                            "ticket": 621204078,
                            "positionId": 621204078,
                            "type": "BUY",
                            "symbol": "USDJPYc",
                            "actualLots": 0.01,
                            "openPrice": 157.144,
                            "actualProfit": -0.75,
                        }
                    ],
                    "pendingOrders": [{"ticket": 1, "symbol": "USDJPYc", "type": "BUY_LIMIT", "volume": 0.01}],
                }
            ),
            encoding="utf-8",
        )
        os.utime(path, (mtime, mtime))
        return path

    def fallback_args(self, endpoint: str) -> argparse.Namespace:
        return argparse.Namespace(endpoint=endpoint, symbol="USDJPYc", group="*", query="", limit=120, symbols_limit=120)

    def test_stale_ea_snapshot_suppresses_positions_and_orders(self):
        old_runtime = os.environ.get("QG_RUNTIME_DIR")
        old_max_age = os.environ.get("QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS")
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime = Path(tmp_dir)
            self.write_dashboard_with_trade_state(runtime, time.time() - 600)
            os.environ["QG_RUNTIME_DIR"] = tmp_dir
            os.environ["QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS"] = "60"
            try:
                positions = bridge.build_ea_snapshot_fallback(self.fallback_args("positions"))
                snapshot = bridge.build_ea_snapshot_fallback(self.fallback_args("snapshot"))
            finally:
                if old_runtime is None:
                    os.environ.pop("QG_RUNTIME_DIR", None)
                else:
                    os.environ["QG_RUNTIME_DIR"] = old_runtime
                if old_max_age is None:
                    os.environ.pop("QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS", None)
                else:
                    os.environ["QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS"] = old_max_age

        self.assertEqual(positions["status"], "STALE_EA_SNAPSHOT")
        self.assertTrue(positions["positions"]["staleSuppressed"])
        self.assertEqual(positions["positions"]["items"], [])
        self.assertEqual(snapshot["positions"]["items"], [])
        self.assertEqual(snapshot["orders"]["items"], [])
        self.assertEqual(snapshot["warning"], "ea_snapshot_stale_positions_and_orders_suppressed")

    def test_fresh_ea_snapshot_keeps_positions(self):
        old_runtime = os.environ.get("QG_RUNTIME_DIR")
        old_max_age = os.environ.get("QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS")
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime = Path(tmp_dir)
            self.write_dashboard_with_trade_state(runtime, time.time())
            os.environ["QG_RUNTIME_DIR"] = tmp_dir
            os.environ["QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS"] = "60"
            try:
                positions = bridge.build_ea_snapshot_fallback(self.fallback_args("positions"))
            finally:
                if old_runtime is None:
                    os.environ.pop("QG_RUNTIME_DIR", None)
                else:
                    os.environ["QG_RUNTIME_DIR"] = old_runtime
                if old_max_age is None:
                    os.environ.pop("QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS", None)
                else:
                    os.environ["QG_MT5_EA_SNAPSHOT_MAX_AGE_SECONDS"] = old_max_age

        self.assertEqual(positions["status"], "EA_SNAPSHOT")
        self.assertEqual(positions["positions"]["count"], 1)
        self.assertEqual(positions["positions"]["items"][0]["ticket"], 621204078)
        self.assertTrue(positions["source"]["fresh"])


if __name__ == "__main__":
    unittest.main()
