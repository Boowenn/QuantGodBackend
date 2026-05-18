from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EA_PATH = ROOT / "MQL5" / "Experts" / "QuantGod_MultiStrategy.mq5"
LIVE_PRESET_PATH = ROOT / "MQL5" / "Presets" / "QuantGod_MT5_HFM_LivePilot.set"
BACKTEST_USDJPY_PATH = ROOT / "MQL5" / "Presets" / "QuantGod_MT5_HFM_Backtest_USDJPYc.set"
BACKTEST_EURUSD_PATH = ROOT / "MQL5" / "Presets" / "QuantGod_MT5_HFM_Backtest_EURUSDc.set"
LIVE_CONFIG_PATH = ROOT / "MQL5" / "Config" / "QuantGod_MT5_HFM_LivePilot.ini"
SHADOW_CONFIG_PATH = ROOT / "MQL5" / "Config" / "QuantGod_MT5_HFM_Shadow.ini"
START_CONFIG_PATH = ROOT / "MQL5" / "Config" / "QuantGod_MT5_Start.ini"
BACKTEST_CONFIG_DIR = ROOT / "MQL5" / "Config" / "BacktestLab"
SHADOW_PRESET_PATH = ROOT / "MQL5" / "Presets" / "QuantGod_MT5_HFM_Shadow.set"
MAC_LAUNCHER_PATH = ROOT / "Start_QuantGod_mac.sh"

USDJPY_SHADOW_ROUTES = (
    "USDJPY_TOKYO_RANGE_BREAKOUT",
    "USDJPY_NIGHT_REVERSION_SAFE",
    "USDJPY_H4_TREND_PULLBACK",
)

USDJPY_SHADOW_ROUTE_SWITCHES = (
    "EnableUsdJpyTokyoBreakoutShadowResearch=true",
    "EnableUsdJpyNightReversionShadowResearch=true",
    "EnableUsdJpyH4PullbackShadowResearch=true",
)


class Mt5RsiExitProtectionTests(unittest.TestCase):
    def test_ea_has_rsi_only_fast_exit_inputs(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn('DashboardBuild      = "QuantGod-v3.17-mt5-startup-entry-guard"', text)
        self.assertIn("input bool   EnablePilotRsiFastExitProtect = true;", text)
        self.assertIn("input int    PilotRsiProtectMinAgeMinutes = 10;", text)
        self.assertIn("input double PilotRsiBreakevenTriggerPips = 5.0;", text)
        self.assertIn("input double PilotRsiTrailingStartPips    = 8.0;", text)
        self.assertIn("input double PilotRsiTrailingDistancePips = 3.5;", text)
        self.assertIn("input double PilotRsiTrailingStepPips     = 0.5;", text)
        self.assertIn("input bool   EnablePilotRsiFailFastProtect = true;", text)
        self.assertIn("input int    PilotRsiFailFastMinAgeMinutes = 120;", text)
        self.assertIn("input double PilotRsiFailFastMinLossPips   = 8.0;", text)
        self.assertIn("input double PilotRsiFailFastMaxLossUSC    = 1.20;", text)
        self.assertIn("input double PilotRsiFailFastStopBufferPips = 2.5;", text)
        self.assertIn("input bool   PilotRsiFailFastCloseOnMaxLoss = true;", text)
        self.assertIn("input bool   EnablePilotRsiTimeStopProtect = true;", text)
        self.assertIn("input int    PilotRsiMaxHoldMinutes       = 90;", text)
        self.assertIn("input bool   PilotRsiCloseOnServerDayChange = true;", text)
        self.assertIn("input bool   PilotRsiBlockSellInUptrend   = true;", text)
        self.assertIn("input bool   PilotRsiRangeTightBuyOnly    = true;", text)
        self.assertIn("input bool   PilotRsiSellLiveBlocked      = true;", text)

    def test_rsi_fast_exit_is_scoped_by_comment(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("bool IsPilotRsiPositionComment(string comment)", text)
        self.assertIn('StringFind(ToUpperString(comment), "QG_RSI_REV")', text)
        self.assertIn("bool isRsiPosition = IsPilotRsiPositionComment(comment);", text)
        self.assertIn("isRsiPosition ? rsiBreakevenOn : baseBreakevenOn", text)
        self.assertIn("isRsiPosition ? MathMax(0, PilotRsiProtectMinAgeMinutes)", text)
        self.assertIn('routeProtect=", (isRsiPosition ? "RSI_FAST" : "BASE")', text)

    def test_rsi_failfast_is_scoped_and_tightens_stops_before_closing(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("void ManagePilotRsiFailFastStops()", text)
        self.assertIn("if(!IsPilotRsiPositionComment(comment))", text)
        self.assertIn("PilotRsiFailFastCloseOnMaxLoss && cashTriggerOn", text)
        self.assertIn("ModifyPilotPositionStops(ticket, symbol, targetSL, currentTP)", text)
        self.assertIn("routeProtect=RSI_FAILFAST", text)
        self.assertIn("ManagePilotRsiFailFastStops();", text)

    def test_rsi_time_stop_and_regime_guards_are_wired(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("void ManagePilotRsiTimeStops()", text)
        self.assertIn("routeProtect=RSI_TIME_STOP", text)
        self.assertIn("ManagePilotRsiTimeStops();", text)
        self.assertIn("PilotRsiBlockSellInUptrend && IsUptrendRegimeLabel(regime.label)", text)
        self.assertIn("PilotRsiRangeTightBuyOnly && IsRangeTightRegimeLabel(regime.label)", text)
        self.assertIn("RSI H1 SELL blocked in", text)
        self.assertIn("PilotRsiSellLiveBlocked && !MQLInfoInteger(MQL_TESTER)", text)
        self.assertIn("RSI SELL live side demoted to shadow/candidate", text)

    def test_usdjpy_strategy_factory_routes_are_shadow_only(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("input bool   EnableUsdJpyTokyoBreakoutShadowResearch = true;", text)
        self.assertIn("input bool   EnableUsdJpyNightReversionShadowResearch = true;", text)
        self.assertIn("input bool   EnableUsdJpyH4PullbackShadowResearch = true;", text)
        self.assertIn("input double ShadowResearchMaxSpreadPips = 3.0;", text)
        self.assertIn("EffectiveShadowResearchMaxSpreadPips()", text)
        self.assertIn("bool IsUsdJpyShadowResearchRoute(string strategyKey)", text)
        self.assertIn("bool IsUsdJpyShadowResearchRouteEnabled(string strategyKey)", text)
        self.assertIn("routeSpreadPips <= EffectiveShadowResearchMaxSpreadPips()", text)
        self.assertIn("spreadGateMode", text)
        self.assertIn("AppendUsdJpyTokyoBreakoutShadowRoute(", text)
        self.assertIn("AppendUsdJpyNightReversionShadowRoute(", text)
        self.assertIn("AppendUsdJpyH4PullbackShadowRoute(", text)
        self.assertIn('"USDJPY_TOKYO_RANGE_BREAKOUT"', text)
        self.assertIn('"USDJPY_NIGHT_REVERSION_SAFE"', text)
        self.assertIn('"USDJPY_H4_TREND_PULLBACK"', text)

        order_send_block = text.split("bool SendPilotMarketOrder", 1)[1].split("void ClosePilotPositions", 1)[0]
        for route in USDJPY_SHADOW_ROUTES:
            self.assertNotIn(route, order_send_block)

    def test_startup_entry_guard_blocks_new_orders_after_ea_reload(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("input bool   EnablePilotStartupEntryGuard = true;", text)
        self.assertIn("input int    PilotStartupEntryMinWaitMinutes = 15;", text)
        self.assertIn("input bool   PilotStartupEntryWaitNextH1Bar = true;", text)
        self.assertIn("datetime g_pilotStartupTime = 0;", text)
        self.assertIn("datetime g_pilotStartupLocalTime = 0;", text)
        self.assertIn("datetime g_pilotStartupH1BarTime = 0;", text)
        self.assertIn("void ArmPilotStartupEntryGuard()", text)
        self.assertIn("bool PilotStartupEntryGuardBlocks(string symbol, string &reason)", text)
        self.assertIn("PilotStartupEntryGuardWaitingForNextH1(symbol)", text)
        self.assertIn("currentH1 <= g_pilotStartupH1BarTime", text)
        self.assertIn("PilotStartupEntryGuardBlocks(symbol, startupReason)", text)
        self.assertIn('"STARTUP_GUARD"', text)
        self.assertIn("startupBlocks", text)
        self.assertIn("startup entry guard strategy=", text)
        self.assertIn("pilotStartupEntryGuardActive", text)

    def test_route_live_switches_are_rechecked_at_order_send(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("bool SendPilotMarketOrder(string symbol, int direction, double slPrice, double tpPrice, string strategyKey)", text)
        self.assertIn('strategyKey == "MA_Cross"', text)
        self.assertIn("if(!EnablePilotMA)", text)
        self.assertIn("IsNonRsiLegacyPilotRoute(strategyKey) && !NonRsiLegacyLiveAuthorizationActive()", text)
        self.assertIn("non-RSI legacy live authorization lock disabled", text)
        self.assertIn("else if(!IsLegacyPilotRouteLiveEnabled(strategyKey))", text)
        self.assertIn("legacy route live switch disabled", text)

    def test_live_trade_permissions_include_account_and_symbol_state(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("string LiveTradePermissionBlocker(string symbol)", text)
        self.assertIn("ACCOUNT_TRADE_DISABLED_OR_INVESTOR_MODE", text)
        self.assertIn("ACCOUNT_EXPERT_TRADE_DISABLED", text)
        self.assertIn("SYMBOL_TRADE_MODE_", text)
        self.assertIn("accountTradeAllowed", text)
        self.assertIn("accountExpertTradeAllowed", text)
        self.assertIn("focusSymbolTradeAllowed", text)
        self.assertIn("tradePermissionBlocker", text)
        self.assertIn('tradeStatus = "ACCOUNT_TRADE_DISABLED";', text)
        self.assertIn('tradeStatus = "SYMBOL_TRADE_DISABLED";', text)
        self.assertIn('tradeStatus = "STARTUP_GUARD";', text)

    def test_live_pilot_does_not_manage_manual_positions_by_default(self):
        ea_text = EA_PATH.read_text(encoding="utf-8")
        preset_text = LIVE_PRESET_PATH.read_text(encoding="utf-8")
        self.assertIn("input bool   EnableManualSafetyGuard    = false;", ea_text)
        self.assertIn("input bool   ManualSafetyCloseOnMaxLoss = false;", ea_text)
        self.assertIn("EnableManualSafetyGuard=false", preset_text)
        self.assertIn("ManualSafetyCloseOnMaxLoss=false", preset_text)
        self.assertIn("if(IsPilotManagedPosition(comment, magic))", ea_text)

    def test_order_send_blocks_investor_mode_before_broker_rejection(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("string permissionBlocker = LiveTradePermissionBlocker(symbol);", text)
        self.assertIn("pilot order blocked: trade permission disabled", text)
        self.assertIn("accountTradeAllowed=", text)
        self.assertIn("accountExpertTradeAllowed=", text)
        self.assertIn("symbolTradeMode=", text)

    def test_non_rsi_legacy_routes_need_second_live_authorization_key(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("input bool   EnableNonRsiLegacyLiveAuthorization = false;", text)
        self.assertIn('input string NonRsiLegacyLiveAuthorizationTag = "";', text)
        self.assertIn("bool IsNonRsiLegacyPilotRoute(string strategyKey)", text)
        self.assertIn("MQLInfoInteger(MQL_TESTER)", text)
        self.assertIn('"ALLOW_NON_RSI_LEGACY_TESTER"', text)
        self.assertIn('"ALLOW_NON_RSI_LEGACY_LIVE"', text)
        self.assertIn("bool NonRsiLegacyLiveAuthorizationActive()", text)
        self.assertIn("return (EnablePilotBBH1Live && NonRsiLegacyLiveAuthorizationActive());", text)
        self.assertIn("return (EnablePilotMacdH1Live && NonRsiLegacyLiveAuthorizationActive());", text)
        self.assertIn("return (EnablePilotSRM15Live && NonRsiLegacyLiveAuthorizationActive());", text)
        self.assertIn('\\"nonRsiLegacyLiveAuthorization\\"', text)
        self.assertIn("nonRsiLegacyLiveAuthorizationState=", text)

    def test_ma_disabled_does_not_disable_legacy_route_loop(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn("if(!IsPilotLiveMode())\n      return;", text)
        self.assertNotIn("if(!IsPilotLiveMode() || !EnablePilotMA)", text)
        self.assertIn('ProcessLegacyPilotRoute("RSI_Reversal"', text)
        self.assertIn('g_maRuntimeStates[i].status = "ROUTE_DISABLED";', text)

    def test_base_ma_exit_defaults_are_not_tightened(self):
        text = LIVE_PRESET_PATH.read_text(encoding="utf-8")
        self.assertIn("PilotBreakevenMinAgeMinutes=60", text)
        self.assertIn("PilotBreakevenTriggerPips=6.0", text)
        self.assertIn("PilotTrailingStartPips=10.0", text)
        self.assertIn("PilotTrailingDistancePips=5.0", text)
        self.assertIn("PilotMaxTotalPositions=2", text)
        self.assertIn("PilotMaxPositionsPerSymbol=2", text)
        self.assertIn("PilotRequireStrategyCommentForManagedPosition=true", text)
        self.assertIn("PilotLotSize=0.01", text)

    def test_live_preset_is_downshifted_to_usdjpy_rsi_iteration(self):
        text = LIVE_PRESET_PATH.read_text(encoding="utf-8")
        self.assertIn("DashboardBuild=QuantGod-v3.17-mt5-startup-entry-guard", text)
        self.assertIn("Watchlist=USDJPY", text)
        self.assertIn("EnablePilotStartupEntryGuard=true", text)
        self.assertIn("PilotStartupEntryMinWaitMinutes=15", text)
        self.assertIn("PilotStartupEntryWaitNextH1Bar=true", text)
        self.assertIn("EnablePilotMA=false", text)
        self.assertIn("EnablePilotRsiH1Live=true", text)
        self.assertIn("EnablePilotBBH1Live=false", text)
        self.assertIn("EnableNonRsiLegacyLiveAuthorization=false", text)
        self.assertIn("NonRsiLegacyLiveAuthorizationTag=", text)
        self.assertIn("EnablePilotMacdH1Live=false", text)
        self.assertIn("EnablePilotSRM15Live=false", text)
        self.assertIn("PilotRsiOverbought=85", text)
        self.assertIn("PilotRsiOversold=15", text)
        self.assertIn("PilotRsiBandTolerancePct=0.006", text)
        self.assertIn("PilotRestrictSession=false", text)
        self.assertIn("PilotSessionStartHour=0", text)
        self.assertIn("PilotSessionEndHour=23", text)
        self.assertIn("PilotNewsPreBlockMinutes=30", text)
        self.assertIn("PilotNewsHighImpactPreBlockMinutes=60", text)
        self.assertIn("PilotNewsPostBlockMinutes=30", text)
        self.assertIn("PilotNewsBiasMinutes=60", text)
        for switch in USDJPY_SHADOW_ROUTE_SWITCHES:
            self.assertIn(switch, text)

    def test_hfm_start_configs_open_usdjpy_chart_for_usdjpy_only_pilot(self):
        for path in (LIVE_CONFIG_PATH, SHADOW_CONFIG_PATH):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Symbol=USDJPYc", text)
            self.assertNotIn("Symbol=EURUSDc", text)

    def test_mt5_configs_raise_chart_history_depth_for_m1_exporter(self):
        config_paths = [
            LIVE_CONFIG_PATH,
            SHADOW_CONFIG_PATH,
            START_CONFIG_PATH,
            *BACKTEST_CONFIG_DIR.glob("*.ini"),
        ]
        for path in config_paths:
            text = path.read_text(encoding="utf-8")
            self.assertIn("[Charts]", text, f"{path} should configure chart history depth")
            self.assertIn("MaxBars=1000000", text, f"{path} should allow 6-12 months of M1 CopyRates")

        start_text = START_CONFIG_PATH.read_text(encoding="utf-8")
        self.assertIn("Symbol=USDJPYc", start_text)
        self.assertNotIn("Symbol=EURUSD", start_text)

    def test_mac_launcher_defaults_to_usdjpy_live_and_agent_v25(self):
        config_text = SHADOW_CONFIG_PATH.read_text(encoding="utf-8")
        self.assertIn("AllowLiveTrading=0", config_text)
        self.assertIn("Symbol=USDJPYc", config_text)

        preset_text = SHADOW_PRESET_PATH.read_text(encoding="utf-8")
        self.assertIn("DashboardBuild=QuantGod-v3.17-mt5-startup-entry-guard", preset_text)
        self.assertIn("Watchlist=USDJPYc", preset_text)
        self.assertIn("PreferredSymbolSuffix=c", preset_text)
        self.assertIn("ShadowMode=true", preset_text)
        self.assertIn("ReadOnlyMode=true", preset_text)
        for switch in USDJPY_SHADOW_ROUTE_SWITCHES:
            self.assertIn(switch, preset_text)

        launcher_text = MAC_LAUNCHER_PATH.read_text(encoding="utf-8")
        self.assertIn('MT5_START_MODE="${QG_MT5_START_MODE:-live}"', launcher_text)
        self.assertIn('MT5_LIVE_LAUNCH_ALLOWED="${QG_MT5_LIVE_LAUNCH_ALLOWED:-1}"', launcher_text)
        self.assertIn("QG_FOCUS_SYMBOL", launcher_text)
        self.assertIn("QG_AUTOMATION_SYMBOLS", launcher_text)
        self.assertIn("QG_ACCOUNT_MODE", launcher_text)
        self.assertIn("quantgod-backend-api", launcher_text)
        self.assertIn("quantgod-frontend-dev", launcher_text)
        self.assertIn("quantgod-agent-v25", launcher_text)
        self.assertIn("quantgod-usdjpy-history-sync", launcher_text)
        self.assertIn("tools/run_mac_agent_v25_loop.sh --loop", launcher_text)
        self.assertIn("tools/ensure_mac_agent_v25_loop.sh --loop", launcher_text)
        self.assertIn("tools/run_mac_usdjpy_history_sync_loop.sh --loop", launcher_text)
        self.assertIn("QG_MT5_TERMINAL_PATH", launcher_text)
        self.assertIn("QG_MT5_PYTHON_BIN", launcher_text)
        self.assertIn("QG_MT5_MAX_BARS", launcher_text)
        self.assertIn("patch_ini_section_key", launcher_text)
        self.assertIn('patch_ini_section_key "$target_config" "Charts" "MaxBars" "$max_bars"', launcher_text)
        self.assertIn('prepare_live_config "$MT5_LIVE_CONFIG" "$MT5_START_SYMBOL" "$QG_MT5_MAX_BARS"', launcher_text)
        self.assertIn('patch_ini_section_key "$MT5_SHADOW_CONFIG" "Charts" "MaxBars" "$QG_MT5_MAX_BARS"', launcher_text)
        self.assertIn("terminal.ini", launcher_text)
        self.assertIn("QG_USDJPY_HISTORY_SYNC_ENABLED", launcher_text)
        self.assertIn("QG_USDJPY_HISTORY_MAX_LAG_HOURS", launcher_text)
        self.assertIn("MT5_SHADOW_SCREEN", launcher_text)
        self.assertIn("MT5_LIVE_SCREEN", launcher_text)
        self.assertIn("MT5_SECONDARY_SCREEN", launcher_text)
        self.assertIn('MT5_SECONDARY_ENABLED="${QG_MT5_SECONDARY_ENABLED:-0}"', launcher_text)
        self.assertIn("QG_MT5_SECONDARY_WINE_PREFIX", launcher_text)
        self.assertIn("QG_MT5_SECONDARY_LOGIN", launcher_text)
        self.assertIn("QG_MT5_SECONDARY_SERVER", launcher_text)
        self.assertIn("QuantGod_MT5_HFM_LiveSecondary_mac.ini", launcher_text)
        self.assertIn("prepare_live_config", launcher_text)
        self.assertIn("terminal64.exe /portable", launcher_text)
        self.assertIn("QuantGod_MT5_HFM_Shadow_mac.ini", launcher_text)
        self.assertIn("QuantGod_MT5_HFM_LivePilot_mac.ini", launcher_text)
        self.assertNotIn("Password=", launcher_text)
        self.assertIn("AllowLiveTrading=0", launcher_text)
        self.assertTrue(
            launcher_text.rstrip().endswith(
                'echo "Screens: $BACKEND_API_SCREEN, $FRONTEND_SCREEN, $AGENT_V25_SUPERVISOR_SCREEN, $AGENT_V25_SCREEN, $HISTORY_SYNC_SCREEN, $MT5_LIVE_SCREEN, $MT5_SECONDARY_SCREEN"'
            )
        )

    def test_live_and_usdjpy_backtest_presets_include_rsi_fast_exit(self):
        for path in (LIVE_PRESET_PATH, BACKTEST_USDJPY_PATH):
            text = path.read_text(encoding="utf-8")
            self.assertIn("EnablePilotRsiFastExitProtect=true", text)
            self.assertIn("PilotRsiProtectMinAgeMinutes=10", text)
            self.assertIn("PilotRsiBreakevenTriggerPips=5.0", text)
            self.assertIn("PilotRsiBreakevenLockPips=1.0", text)
            self.assertIn("PilotRsiTrailingStartPips=8.0", text)
            self.assertIn("PilotRsiTrailingDistancePips=3.5", text)
            self.assertIn("PilotRsiTrailingStepPips=0.5", text)
            self.assertIn("EnablePilotRsiFailFastProtect=true", text)
            self.assertIn("PilotRsiFailFastMinAgeMinutes=120", text)
            self.assertIn("PilotRsiFailFastMinLossPips=8.0", text)
            self.assertIn("PilotRsiFailFastMaxLossUSC=1.20", text)
            self.assertIn("PilotRsiFailFastStopBufferPips=2.5", text)
            self.assertIn("PilotRsiFailFastStepPips=0.5", text)
            self.assertIn("PilotRsiFailFastCloseOnMaxLoss=true", text)
            self.assertIn("EnablePilotRsiTimeStopProtect=true", text)
            self.assertIn("PilotRsiMaxHoldMinutes=90", text)
            self.assertIn("PilotRsiCloseOnServerDayChange=true", text)
            self.assertIn("PilotRsiBlockSellInUptrend=true", text)
            self.assertIn("PilotRsiRangeTightBuyOnly=true", text)
            for switch in USDJPY_SHADOW_ROUTE_SWITCHES:
                self.assertIn(switch, text)

    def test_eurusd_backtest_only_authorizes_non_rsi_legacy_routes_in_tester(self):
        text = BACKTEST_EURUSD_PATH.read_text(encoding="utf-8")
        self.assertIn("DashboardBuild=QuantGod-v3.17-mt5-startup-entry-guard-backtest", text)
        self.assertIn("EnablePilotStartupEntryGuard=false", text)
        self.assertIn("PilotStartupEntryMinWaitMinutes=0", text)
        self.assertIn("PilotStartupEntryWaitNextH1Bar=false", text)
        self.assertIn("EnablePilotBBH1Live=true", text)
        self.assertIn("EnablePilotMacdH1Live=true", text)
        self.assertIn("EnablePilotSRM15Live=true", text)
        self.assertIn("EnableNonRsiLegacyLiveAuthorization=true", text)
        self.assertIn("NonRsiLegacyLiveAuthorizationTag=ALLOW_NON_RSI_LEGACY_TESTER", text)

    def test_shadow_outcome_unknown_direction_keeps_opportunity_signal(self):
        text = EA_PATH.read_text(encoding="utf-8")
        self.assertIn('return "LONG_OPPORTUNITY";', text)
        self.assertIn('return "SHORT_OPPORTUNITY";', text)
        self.assertIn('return "NEUTRAL_OPPORTUNITY";', text)


if __name__ == "__main__":
    unittest.main()
