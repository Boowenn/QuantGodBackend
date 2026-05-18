import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_daily_autopilot.py"
TOOLS_DIR = str(MODULE_PATH.parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
SPEC = importlib.util.spec_from_file_location("run_daily_autopilot", MODULE_PATH)
autopilot = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(autopilot)

REVIEW_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "build_daily_review.py"
REVIEW_SPEC = importlib.util.spec_from_file_location("build_daily_review", REVIEW_MODULE_PATH)
daily_review = importlib.util.module_from_spec(REVIEW_SPEC)
assert REVIEW_SPEC.loader is not None
REVIEW_SPEC.loader.exec_module(daily_review)

GUARD_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "auto_tester_window_guard.py"
GUARD_SPEC = importlib.util.spec_from_file_location("auto_tester_window_guard", GUARD_MODULE_PATH)
auto_tester_guard = importlib.util.module_from_spec(GUARD_SPEC)
assert GUARD_SPEC.loader is not None
GUARD_SPEC.loader.exec_module(auto_tester_guard)

AUTO_TESTER_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_param_lab_auto_tester_window.py"
AUTO_TESTER_SPEC = importlib.util.spec_from_file_location("run_param_lab_auto_tester_window", AUTO_TESTER_MODULE_PATH)
auto_tester_window = importlib.util.module_from_spec(AUTO_TESTER_SPEC)
assert AUTO_TESTER_SPEC.loader is not None
AUTO_TESTER_SPEC.loader.exec_module(auto_tester_window)

WATCHER_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "watch_param_lab_reports.py"
WATCHER_SPEC = importlib.util.spec_from_file_location("watch_param_lab_reports", WATCHER_MODULE_PATH)
watcher = importlib.util.module_from_spec(WATCHER_SPEC)
assert WATCHER_SPEC.loader is not None
WATCHER_SPEC.loader.exec_module(watcher)

POLY_GOV_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "build_polymarket_auto_governance.py"
POLY_GOV_SPEC = importlib.util.spec_from_file_location("build_polymarket_auto_governance", POLY_GOV_MODULE_PATH)
poly_governance = importlib.util.module_from_spec(POLY_GOV_SPEC)
assert POLY_GOV_SPEC.loader is not None
POLY_GOV_SPEC.loader.exec_module(poly_governance)

POLY_RESEARCH_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "build_polymarket_research_bridge.py"
POLY_RESEARCH_SPEC = importlib.util.spec_from_file_location("build_polymarket_research_bridge", POLY_RESEARCH_MODULE_PATH)
poly_research = importlib.util.module_from_spec(POLY_RESEARCH_SPEC)
assert POLY_RESEARCH_SPEC.loader is not None
sys.modules[POLY_RESEARCH_SPEC.name] = poly_research
POLY_RESEARCH_SPEC.loader.exec_module(poly_research)

PARAM_RUN_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_param_lab.py"
PARAM_RUN_SPEC = importlib.util.spec_from_file_location("run_param_lab", PARAM_RUN_MODULE_PATH)
param_runner = importlib.util.module_from_spec(PARAM_RUN_SPEC)
assert PARAM_RUN_SPEC.loader is not None
PARAM_RUN_SPEC.loader.exec_module(param_runner)

PARAM_COLLECT_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "collect_param_lab_results.py"
PARAM_COLLECT_SPEC = importlib.util.spec_from_file_location("collect_param_lab_results", PARAM_COLLECT_MODULE_PATH)
param_collect = importlib.util.module_from_spec(PARAM_COLLECT_SPEC)
assert PARAM_COLLECT_SPEC.loader is not None
PARAM_COLLECT_SPEC.loader.exec_module(param_collect)


class DailyAutopilotTests(unittest.TestCase):
    def test_daily_autopilot_uses_bounded_daily_tester_range(self):
        now = datetime.fromisoformat("2026-05-02T00:25:00+09:00")

        self.assertEqual(autopilot.daily_tester_date_range(now, 2), ("2026.04.30", "2026.05.02"))
        self.assertEqual(autopilot.daily_tester_date_range(now, 99), ("2026.04.18", "2026.05.02"))
        self.assertEqual(autopilot.daily_tester_timeout_seconds(120), 300)
        self.assertEqual(autopilot.daily_tester_timeout_seconds(99999), 3600)

    def test_mac_autopilot_resolves_existing_hfm_root_from_mt5_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_dir = root / "MetaTrader 5" / "MQL5" / "Files"
            runtime_dir.mkdir(parents=True)

            self.assertEqual(autopilot.resolve_hfm_root(root, runtime_dir, ""), runtime_dir.parent.parent)

    def test_mac_autopilot_prefers_live_mt5_files_when_dashboard_default_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mac_files = root / "MetaTrader 5" / "MQL5" / "Files"
            mac_files.mkdir(parents=True)
            (mac_files / "QuantGod_Dashboard.json").write_text("{}", encoding="utf-8")
            original = autopilot.mac_mt5_files_dir
            old_mode = os.environ.get("QG_MAC_RUNTIME_SOURCE")
            autopilot.mac_mt5_files_dir = lambda: mac_files
            os.environ["QG_MAC_RUNTIME_SOURCE"] = "auto"
            try:
                self.assertEqual(autopilot.resolve_runtime_dir(root, ""), mac_files)
            finally:
                autopilot.mac_mt5_files_dir = original
                if old_mode is None:
                    os.environ.pop("QG_MAC_RUNTIME_SOURCE", None)
                else:
                    os.environ["QG_MAC_RUNTIME_SOURCE"] = old_mode

    def test_watcher_preserves_absolute_posix_report_path(self):
        repo_root = Path("/Users/bowen/Desktop/Quard/QuantGodBackend")
        raw = "/Users/bowen/Desktop/Quard/QuantGodBackend/archive/param-lab/runs/run/reports/EURUSDc/x.html"

        self.assertEqual(watcher.normalize_report_path(raw, repo_root), Path(raw))

    def test_watcher_repairs_repo_prefixed_wine_report_path(self):
        repo_root = Path("/Users/bowen/Desktop/Quard/QuantGodBackend")
        raw = (
            "/Users/bowen/Desktop/Quard/QuantGodBackend/"
            "\\Users\\bowen\\Desktop\\Quard\\QuantGodBackend\\archive\\param-lab\\runs\\run\\reports\\EURUSDc\\x.html"
        )

        self.assertEqual(
            watcher.normalize_report_path(raw, repo_root),
            Path("/Users/bowen/Desktop/Quard/QuantGodBackend/archive/param-lab/runs/run/reports/EURUSDc/x.html"),
        )

    def test_watcher_remaps_legacy_monorepo_report_path_after_split(self):
        repo_root = Path("/Users/bowen/Desktop/Quard/QuantGodBackend")
        raw = "/Users/bowen/Desktop/Quard/" + "Quant" + "God/archive/param-lab/runs/run/reports/EURUSDc/x.html"

        self.assertEqual(
            watcher.normalize_report_path(raw, repo_root),
            Path("/Users/bowen/Desktop/Quard/QuantGodBackend/archive/param-lab/runs/run/reports/EURUSDc/x.html"),
        )

    def test_watcher_remaps_legacy_monorepo_wine_report_path_after_split(self):
        repo_root = Path("/Users/bowen/Desktop/Quard/QuantGodBackend")
        raw = r"Z:\Users\bowen\Desktop\Quard\\" + "Quant" + r"God\archive\param-lab\runs\run\reports\EURUSDc\x.html"

        self.assertEqual(
            watcher.normalize_report_path(raw, repo_root),
            Path("/Users/bowen/Desktop/Quard/QuantGodBackend/archive/param-lab/runs/run/reports/EURUSDc/x.html"),
        )

    def test_auto_tester_runner_command_forwards_daily_bounds_and_timeout(self):
        args = type("Args", (), {
            "repo_root": str(MODULE_PATH.parents[1]),
            "runtime_dir": "/tmp/runtime",
            "max_tasks": 1,
            "rank_mode": "route-balanced",
            "login": "186054398",
            "server": "HFMarketsGlobal-Live12",
            "max_live_snapshot_age_minutes": 30,
            "from_date": "2026.04.30",
            "to_date": "2026.05.02",
            "terminal_timeout_seconds": 900,
            "route": [],
            "candidate_id": [],
            "allow_outside_window": False,
        })()

        command = auto_tester_window.command_for_runner(
            args,
            run_terminal=True,
            lock_path=Path("/tmp/runtime/QuantGod_AutoTesterWindow.lock.json"),
            plan_path=Path("/tmp/runtime/QuantGod_AutoTesterWindowExecutorPlan.json"),
            hfm_root=Path("/tmp/isolated_tester"),
        )

        self.assertIn("--from-date", command)
        self.assertIn("2026.04.30", command)
        self.assertIn("--to-date", command)
        self.assertIn("2026.05.02", command)
        self.assertIn("--terminal-timeout-seconds", command)
        self.assertIn("900", command)

    def test_agent_artifacts_turn_missing_html_into_parsed_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_dir = Path(tmp)
            (artifact_dir / "QuantGod_TradeJournal.csv").write_text(
                "DealTicket,PositionId,EventType,Side,Symbol,Lots,Price,GrossProfit,Commission,Swap,NetProfit,EventTime,Strategy,Source,Regime,RegimeTimeframe,Comment\n",
                encoding="utf-8",
            )
            (artifact_dir / "QuantGod_CloseHistory.csv").write_text(
                "ExitTicket,PositionId,Type,Symbol,Lots,OpenTime,CloseTime,DurationMinutes,OpenPrice,ClosePrice,GrossProfit,Commission,Swap,NetProfit,Strategy,Source,EntryRegime,ExitRegime,RegimeTimeframe,Comment\n",
                encoding="utf-8",
            )
            (artifact_dir / "QuantGod_Dashboard.json").write_text(
                json.dumps({"runtime": {"tradeStatus": "READY", "executionEnabled": True, "readOnlyMode": False}, "account": {"balance": 10000.0}}),
                encoding="utf-8",
            )

            metrics = param_runner.parse_agent_artifacts(
                artifact_dir,
                {
                    "reportExists": False,
                    "parseStatus": "REPORT_MISSING",
                    "closedTrades": None,
                    "netProfit": None,
                    "profitFactor": None,
                    "winRate": None,
                },
            )

        self.assertTrue(metrics["reportExists"])
        self.assertTrue(metrics["testerEvidenceExists"])
        self.assertEqual(metrics["parseStatus"], "PARSED_AGENT_ARTIFACTS")
        self.assertEqual(metrics["closedTrades"], 0)
        self.assertEqual(metrics["sampleStatus"], "NO_TRADES_IN_TEST_WINDOW")

    def test_collector_reuses_agent_metrics_from_status(self):
        task = {
            "metrics": {
                "reportExists": True,
                "testerEvidenceExists": True,
                "parseStatus": "PARSED_AGENT_ARTIFACTS",
                "closedTrades": 0,
                "netProfit": 0.0,
            }
        }

        metrics = param_collect.reusable_task_metrics(task)
        score, grade, readiness, blockers = param_collect.score_result(metrics, min_trades=10)

        self.assertEqual(metrics["parseStatus"], "PARSED_AGENT_ARTIFACTS")
        self.assertEqual(grade, "C")
        self.assertEqual(readiness, "NEEDS_MORE_EVIDENCE")
        self.assertIn("trades_lt_min", blockers)

    def test_run_step_passes_env_overrides_without_order_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = autopilot.run_step(
                "env_probe",
                [
                    sys.executable,
                    "-c",
                    "import os; print(os.environ['QG_RUNTIME_DIR']); print(os.environ['QG_MAC_RUNTIME_SOURCE'])",
                ],
                tmp_path,
                env_overrides={
                    "QG_RUNTIME_DIR": str(tmp_path / "runtime"),
                    "QG_MAC_RUNTIME_SOURCE": "local",
                },
            )

            self.assertEqual(result["status"], "OK")
            self.assertIn(str(tmp_path / "runtime"), result["stdoutTail"])
            self.assertIn("local", result["stdoutTail"])

    def test_mac_wrappers_are_valid_bash(self):
        repo_root = MODULE_PATH.parents[1]
        env = {**os.environ, "QG_MAC_RUNTIME_SOURCE": "local"}
        result = subprocess.run(
            [
                "bash",
                "-n",
                "tools/run_mac_daily_autopilot.sh",
                "tools/run_mac_agent_v25_loop.sh",
                "tools/ensure_mac_agent_v25_loop.sh",
                "tools/run_mac_usdjpy_history_sync_loop.sh",
                "tools/run_mac_polymarket_readonly_cycle.sh",
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mac_daily_wrapper_defaults_to_agent_v25(self):
        repo_root = MODULE_PATH.parents[1]
        wrapper = (repo_root / "tools" / "run_mac_daily_autopilot.sh").read_text(encoding="utf-8")
        self.assertIn("QG_LEGACY_DAILY_AUTOPILOT_ENABLED", wrapper)
        self.assertIn("tools/run_mac_agent_v25_loop.sh", wrapper)
        self.assertIn("tools/run_daily_autopilot.py", wrapper)

        agent_loop = (repo_root / "tools" / "run_mac_agent_v25_loop.sh").read_text(encoding="utf-8")
        self.assertIn("run_daily_autopilot_v2.py", agent_loop)
        self.assertIn("--symbols USDJPYc", agent_loop)
        self.assertIn("QG_AGENT_V25_INTERVAL_SECONDS", agent_loop)
        self.assertIn("QG_TELEGRAM_COMMANDS_ALLOWED", agent_loop)
        self.assertIn("QuantGod_AgentV25LoopStatus.json", agent_loop)
        self.assertIn("run_mac_agent_v25_maintenance.py", agent_loop)
        self.assertIn("QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS", agent_loop)
        self.assertIn("--force-burn-in", agent_loop)
        self.assertIn("QG_AGENT_V25_LOCK_DIR", agent_loop)
        self.assertIn("acquire_loop_lock", agent_loop)
        self.assertIn("release_loop_lock", agent_loop)

        supervisor = (repo_root / "tools" / "ensure_mac_agent_v25_loop.sh").read_text(encoding="utf-8")
        self.assertIn("QuantGod_AgentV25LoopStatus.json", supervisor)
        self.assertIn("QuantGod_AgentV25SupervisorStatus.json", supervisor)
        self.assertIn("QG_AGENT_V25_STALE_SECONDS", supervisor)
        self.assertIn("run_mac_agent_v25_loop.sh --loop", supervisor)
        self.assertIn("run_mac_agent_v25_maintenance.py", supervisor)
        self.assertIn("QG_AGENT_OPS_HEALTH_ENABLED", supervisor)

        launcher = (repo_root / "Start_QuantGod_mac.sh").read_text(encoding="utf-8")
        self.assertIn("quantgod-agent-v25-supervisor", launcher)
        self.assertIn("tools/ensure_mac_agent_v25_loop.sh --loop", launcher)

    def test_mac_history_sync_wrapper_uses_mt5_python_and_terminal_path(self):
        repo_root = MODULE_PATH.parents[1]
        script = (repo_root / "tools" / "run_mac_usdjpy_history_sync_loop.sh").read_text(encoding="utf-8")
        self.assertIn("sync-klines", script)
        self.assertIn("QG_MT5_TERMINAL_PATH", script)
        self.assertIn("QG_MT5_PYTHON_BIN", script)
        self.assertIn("QG_USDJPY_HISTORY_MONTHS", script)
        self.assertIn("QG_USDJPY_HISTORY_TIMEFRAMES", script)
        self.assertIn("QG_USDJPY_HISTORY_INTERVAL_SECONDS", script)
        self.assertIn("QG_USDJPY_HISTORY_MAX_BARS", script)
        self.assertIn("QG_USDJPY_HISTORY_MAX_LAG_HOURS", script)
        self.assertIn("--terminal-path", script)
        self.assertIn("--max-bars-per-timeframe", script)
        self.assertIn("--max-latest-lag-hours", script)
        self.assertIn("tools/run_usdjpy_strategy_backtest.py --runtime-dir \"$RUNTIME_DIR\" quality", script)

    def test_mt5_permission_log_is_not_triage_when_current_dashboard_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            mt5_root = Path(tmp) / "MetaTrader 5"
            runtime_dir = mt5_root / "MQL5" / "Files"
            logs_dir = mt5_root / "MQL5" / "Logs"
            runtime_dir.mkdir(parents=True)
            logs_dir.mkdir(parents=True)
            (logs_dir / "20260501.log").write_text(
                "pilot order failed: retcode=10017 comment=Trade disabled\n"
                "trading has been disabled - investor mode\n",
                encoding="utf-8",
            )
            (runtime_dir / "QuantGod_Dashboard.json").write_text(json.dumps({
                "runtime": {
                    "tradeStatus": "READY",
                    "tradeAllowed": True,
                    "terminalTradeAllowed": True,
                    "programTradeAllowed": True,
                    "accountTradeAllowed": True,
                    "accountExpertTradeAllowed": True,
                    "focusSymbolTradeAllowed": True,
                    "tradePermissionBlocker": "",
                }
            }), encoding="utf-8")

            risk = daily_review.mt5_terminal_risk(runtime_dir, datetime(2026, 5, 1, tzinfo=timezone.utc))

            self.assertGreater(risk["investorModeCount"], 0)
            self.assertGreater(risk["orderSendFailureCount"], 0)
            self.assertTrue(risk["currentTradePermissionRecovered"])
            self.assertFalse(risk["requiresCodexReview"])

    def test_dashboard_server_exposes_daily_readonly_routes(self):
        server_source = (MODULE_PATH.parents[1] / "Dashboard" / "dashboard_server.js").read_text(encoding="utf-8")

        self.assertIn("'/api/daily-review'", server_source)
        self.assertIn("'/api/daily-autopilot'", server_source)
        self.assertIn("dailyReviewName", server_source)
        self.assertIn("buildDailyTesterBounds", server_source)
        self.assertIn("'--terminal-timeout-seconds'", server_source)
        self.assertIn("'--from-date'", server_source)
        self.assertIn(
            "build_polymarket_research_bridge.py",
            (MODULE_PATH.parents[1] / "tools" / "run_mac_polymarket_readonly_cycle.sh").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "build_polymarket_retune_planner.py",
            (MODULE_PATH.parents[1] / "tools" / "run_mac_polymarket_readonly_cycle.sh").read_text(encoding="utf-8"),
        )

    def test_daily_pnl_negative_is_resolved_when_rsi_sell_side_is_blocked(self):
        daily_pnl = daily_review.close_history_summary([
            {
                "CloseTime": "2026.04.29 09:00",
                "Strategy": "RSI_Reversal",
                "Type": "SELL",
                "NetProfit": "-0.70",
            },
            {
                "CloseTime": "2026.04.29 15:00",
                "Strategy": "RSI_Reversal",
                "Type": "SELL",
                "NetProfit": "-0.55",
            },
        ])
        governance = {
            "routeDecisions": [{
                "key": "RSI_Reversal",
                "sidePolicy": {"sellLiveAllowed": False},
            }]
        }

        self.assertTrue(daily_review.daily_pnl_resolved_by_policy(daily_pnl, governance))

        governance["routeDecisions"][0]["sidePolicy"]["sellLiveAllowed"] = True
        self.assertFalse(daily_review.daily_pnl_resolved_by_policy(daily_pnl, governance))

    def test_daily_pnl_uses_requested_review_day_even_without_trades(self):
        daily_pnl = daily_review.close_history_summary([
            {
                "CloseTime": "2026.04.29 09:00",
                "Strategy": "RSI_Reversal",
                "Type": "SELL",
                "NetProfit": "-0.70",
            }
        ], "2026-04-30")

        self.assertEqual(daily_pnl["date"], "2026-04-30")
        self.assertEqual(daily_pnl["closedTrades"], 0)
        self.assertEqual(daily_pnl["netUSC"], 0)
        self.assertEqual(daily_pnl["byStrategy"], [])

    def test_param_action_queue_marks_window_wait_as_scheduled(self):
        scheduler = {
            "selectedTasks": [{
                "candidateId": "MA_Cross_USDJPYc_ma_control_tight_exit",
                "routeKey": "MA_Cross",
                "score": 1.074,
                "resultStatus": "CONFIG_ONLY_WAIT_REPORT",
            }]
        }
        auto_tester = {
            "summary": {"canRunTerminal": False},
            "gate": {"blockers": ["outside_strategy_tester_window"]},
        }

        queue = daily_review.param_action_queue(scheduler, auto_tester, 5)

        self.assertEqual(queue[0]["state"], "WAIT_GUARD")
        self.assertEqual(queue[0]["guardClass"], "WAIT_TESTER_WINDOW")
        self.assertEqual(queue[0]["statusLabel"], "SCHEDULED_TESTER_WINDOW")
        self.assertIn("nextWindowLabel", queue[0])
        self.assertFalse(queue[0]["livePresetMutationAllowed"])

    def test_param_action_queue_marks_terminal_nonzero_as_codex_triage(self):
        scheduler = {
            "selectedTasks": [{
                "candidateId": "MA_Cross_USDJPYc_ma_control_tight_exit",
                "routeKey": "MA_Cross",
                "score": 1.074,
                "resultStatus": "REPORT_MISSING_AFTER_RUN",
            }]
        }
        auto_tester = {
            "summary": {"canRunTerminal": True},
            "gate": {"blockers": []},
        }
        run_recovery = {
            "candidateDrilldown": [{
                "candidateId": "MA_Cross_USDJPYc_ma_control_tight_exit",
                "riskLevel": "red",
                "riskReason": "terminal_nonzero",
                "latestStopReason": "terminal_nonzero",
                "terminalNonzeroCount": 1,
                "terminalExitCodes": [191],
                "failureReasons": {
                    "terminal_exit_nonzero": 1,
                    "report_missing_after_run": 1,
                },
            }]
        }

        queue = daily_review.param_action_queue(scheduler, auto_tester, 5, run_recovery)

        self.assertEqual(queue[0]["state"], "NEEDS_CODEX_TRIAGE")
        self.assertEqual(queue[0]["guardClass"], "RUN_RECOVERY_RED")
        self.assertEqual(queue[0]["statusLabel"], "TERMINAL_EXIT_NONZERO")
        self.assertIn("terminal_exit_191", queue[0]["blockers"])
        self.assertEqual(queue[0]["recovery"]["riskLevel"], "red")
        self.assertFalse(queue[0]["livePresetMutationAllowed"])

    def test_param_action_queue_treats_synced_account_context_as_window_wait(self):
        scheduler = {
            "selectedTasks": [{
                "candidateId": "MA_Cross_USDJPYc_ma_control_tight_exit",
                "routeKey": "MA_Cross",
                "score": 1.074,
                "resultStatus": "CONFIG_ONLY_WAIT_REPORT",
            }]
        }
        auto_tester = {
            "summary": {"canRunTerminal": False},
            "gate": {"blockers": ["outside_strategy_tester_window"]},
        }
        run_recovery = {
            "candidateDrilldown": [{
                "candidateId": "MA_Cross_USDJPYc_ma_control_tight_exit",
                "riskLevel": "yellow",
                "riskReason": "account_context_synced_retry_ready",
                "latestStopReason": "account_context_synced_retry_ready",
                "terminalNonzeroCount": 3,
                "terminalExitCodes": [191],
            }]
        }

        queue = daily_review.param_action_queue(scheduler, auto_tester, 5, run_recovery)

        self.assertEqual(queue[0]["state"], "WAIT_GUARD")
        self.assertEqual(queue[0]["guardClass"], "WAIT_TESTER_WINDOW")
        self.assertEqual(queue[0]["statusLabel"], "ACCOUNT_CONTEXT_SYNCED_RETRY_READY")
        self.assertFalse(queue[0]["livePresetMutationAllowed"])

    def test_param_action_queue_marks_latest_parsed_agent_evidence_done(self):
        scheduler = {
            "selectedTasks": [{
                "candidateId": "MA_Cross_USDJPYc_ma_control_tight_exit",
                "routeKey": "MA_Cross",
                "score": 1.074,
                "resultStatus": "REPORT_MISSING_AFTER_RUN",
            }]
        }
        auto_tester = {
            "summary": {"canRunTerminal": True},
            "gate": {"blockers": []},
        }
        run_recovery = {
            "candidateDrilldown": [{
                "candidateId": "MA_Cross_USDJPYc_ma_control_tight_exit",
                "riskLevel": "green",
                "riskReason": "parsed_latest",
                "latestState": "parsed",
                "latestStopReason": "parsed_latest",
            }]
        }

        queue = daily_review.param_action_queue(scheduler, auto_tester, 5, run_recovery)

        self.assertEqual(queue[0]["state"], "DONE")
        self.assertFalse(queue[0]["livePresetMutationAllowed"])

    def test_daily_tester_budget_suppresses_new_backlog_after_today_run(self):
        now = datetime.fromisoformat("2026-05-02T04:05:00+09:00")
        param_status = {
            "generatedAtIso": "2026-05-01T18:32:59+00:00",
            "summary": {
                "runAttemptedCount": 5,
                "reportParsedCount": 5,
                "agentEvidenceParsedCount": 5,
                "selectedTaskCount": 5,
            },
        }

        completed = daily_review.daily_tester_completed_count(param_status, now, 5)

        self.assertEqual(completed, 5)

    def test_ready_tasks_roll_to_research_backlog_after_clean_daily_run(self):
        action_queue = [{
            "candidateId": "BB_Triple_EURUSDc_bb_current_control",
            "state": "READY_TO_RUN_TESTER",
        }]
        completed_queue = [{
            "candidateId": "RSI_Reversal_USDJPYc_rsi_extreme_crossback_v2",
            "state": "DONE",
        }]
        recovery_summary = {"riskRedCount": 0, "riskYellowCount": 0}

        self.assertTrue(daily_review.should_roll_ready_tasks_to_research_backlog(
            action_queue,
            completed_queue,
            7,
            recovery_summary,
        ))

    def test_ready_tasks_stay_actionable_when_recovery_risk_remains(self):
        action_queue = [{"state": "READY_TO_RUN_TESTER"}]
        completed_queue = [{"state": "DONE"}]
        recovery_summary = {"riskRedCount": 0, "riskYellowCount": 1}

        self.assertFalse(daily_review.should_roll_ready_tasks_to_research_backlog(
            action_queue,
            completed_queue,
            7,
            recovery_summary,
        ))

    def test_daily_iteration_flags_all_no_trade_tester_reports(self):
        tester_tasks = [
            {"candidateId": "BB_Triple_EURUSDc_a", "routeKey": "BB_Triple", "closedTrades": 0},
            {"candidateId": "MACD_Divergence_EURUSDc_b", "routeKey": "MACD_Divergence", "closedTrades": 0},
        ]

        iteration = daily_review.daily_iteration_review(
            {"date": "2026-05-01", "closedTrades": 0, "netUSC": 0.0},
            [],
            {"dailyReview": {"summary": {"lossQuarantine": False}}},
            {"requiresCodexReview": False},
            5,
            tester_tasks,
        )

        self.assertEqual(iteration["status"], "REVIEW_COMPLETE_NO_CODE_CHANGE")
        self.assertEqual(iteration["findings"][-1]["code"], "PARAMLAB_NO_TRADE_TESTER_WINDOWS")
        self.assertTrue(iteration["findings"][-1]["iterationApplied"])
        self.assertEqual(iteration["strategyIterationQueue"][-1]["type"], "PARAMLAB_NO_TRADE_RETUNE")
        self.assertEqual(iteration["strategyIterationQueue"][-1]["status"], "RETUNE_PLAN_READY_TESTER_ONLY")
        self.assertTrue(iteration["strategyIterationQueue"][-1]["routePlans"])
        self.assertFalse(iteration["strategyIterationQueue"][-1]["livePresetMutationAllowed"])

    def test_daily_iteration_does_not_require_strategy_iteration_for_manual_mt5_loss(self):
        iteration = daily_review.daily_iteration_review(
            {
                "date": "2026-05-05",
                "closedTrades": 1,
                "netUSC": -1.62,
                "lossByStrategySide": [{
                    "strategy": "Manual/Other",
                    "side": "BUY",
                    "trades": 1,
                    "netUSC": -1.62,
                }],
            },
            [],
            {"dailyReview": {"summary": {"lossQuarantine": False}}},
            {"requiresCodexReview": False},
            5,
        )

        self.assertEqual(iteration["status"], "REVIEW_COMPLETE_NO_CODE_CHANGE")
        self.assertFalse(iteration["codexFollowupRequired"])
        self.assertEqual(iteration["findings"][0]["code"], "MT5_DAILY_PNL_NEGATIVE")
        self.assertTrue(iteration["findings"][0]["iterationApplied"])
        self.assertFalse(iteration["findings"][0]["requiresStrategyIteration"])

    def test_daily_iteration_flags_polymarket_loss_quarantine_for_codex(self):
        poly = {
            "dailyReview": {
                "summary": {
                    "lossQuarantine": True,
                    "executedProfitFactor": 0.0145,
                    "shadowProfitFactor": 0.7055,
                    "quarantineCount": 45,
                },
                "topLossSources": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "profitFactor": 0.3956,
                    "winRatePct": 19.35,
                    "realizedPnl": -58.0649,
                }],
                "retuneSources": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                }],
                "copyTradingReview": {
                    "active": True,
                    "status": "COPY_TRADING_RETUNE_REQUIRED",
                    "summary": "正在模拟跨市场跟单策略，等待重调。",
                    "bestExperimentKey": "copy_archive_all_markets_v1",
                },
                "copyRetuneSources": [{
                    "experimentKey": "copy_archive_all_markets_v1",
                    "routeFamily": "copy_archive",
                }],
            }
        }
        iteration = daily_review.daily_iteration_review(
            {"date": "2026-05-01", "closedTrades": 2, "netUSC": 3.54},
            [],
            poly,
            {"requiresCodexReview": False},
            5,
        )
        codex = daily_review.codex_review_queue(
            {"date": "2026-05-01", "closedTrades": 2, "netUSC": 3.54, "requiresReview": False},
            [],
            [],
            {},
            {},
            {},
            {"workerStatus": "OK"},
            {"requiresCodexReview": False},
            iteration,
        )

        self.assertEqual(iteration["status"], "ITERATION_REQUIRED")
        self.assertTrue(iteration["codexFollowupRequired"])
        self.assertTrue(iteration["codeIterationQueue"])
        self.assertTrue(iteration["strategyIterationQueue"])
        self.assertTrue(codex["required"])
        self.assertEqual(codex["reasons"][-1]["code"], "DAILY_ITERATION_ACTIONABLE_FINDINGS")

    def test_daily_iteration_keeps_fresh_polymarket_retune_visible_for_review(self):
        poly = {
            "dailyReview": {
                "summary": {
                    "lossQuarantine": True,
                    "reviewFreshForDay": True,
                    "executedProfitFactor": 0.0145,
                    "shadowProfitFactor": 0.7055,
                    "quarantineCount": 45,
                    "retuneTotal": 6,
                    "retuneRed": 3,
                    "retuneYellow": 2,
                },
                "topLossSources": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "profitFactor": 0.3956,
                    "winRatePct": 19.35,
                    "realizedPnl": -58.0649,
                }],
                "retuneSources": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                }],
                "copyTradingReview": {
                    "active": True,
                    "status": "COPY_TRADING_RETUNE_REQUIRED",
                    "summary": "正在模拟跨市场跟单策略，等待重调。",
                    "bestExperimentKey": "copy_archive_all_markets_v1",
                },
                "copyRetuneSources": [{
                    "experimentKey": "copy_archive_all_markets_v1",
                    "routeFamily": "copy_archive",
                }],
            }
        }
        iteration = daily_review.daily_iteration_review(
            {"date": "2026-05-01", "closedTrades": 2, "netUSC": 3.54},
            [],
            poly,
            {"requiresCodexReview": False},
            5,
        )
        codex = daily_review.codex_review_queue(
            {"date": "2026-05-01", "closedTrades": 2, "netUSC": 3.54, "requiresReview": False},
            [],
            [],
            {},
            {},
            {},
            {"workerStatus": "OK"},
            {"requiresCodexReview": False},
            iteration,
        )

        self.assertEqual(iteration["status"], "REVIEW_COMPLETE_NO_CODE_CHANGE")
        self.assertFalse(iteration["codexFollowupRequired"])
        self.assertEqual(iteration["codeIterationQueue"][0]["status"], "APPLIED_SHADOW_ONLY")
        self.assertEqual(iteration["strategyIterationQueue"][0]["status"], "APPLIED_SHADOW_ONLY")
        self.assertEqual(iteration["strategyIterationQueue"][1]["type"], "POLYMARKET_COPY_TRADING_RETUNE")
        self.assertEqual(iteration["strategyIterationQueue"][1]["status"], "RETUNE_SPEC_READY_SHADOW_ONLY")
        self.assertIn("任何市场模块", iteration["strategyIterationQueue"][1]["recommendation"])
        self.assertFalse(codex["required"])

    def test_daily_iteration_treats_existing_polymarket_retune_plan_as_agent_completed(self):
        poly = {
            "dailyReview": {
                "summary": {
                    "lossQuarantine": True,
                    "reviewFreshForDay": False,
                    "retunePlanReady": True,
                    "retuneAgentStatus": "RETUNE_PLAN_READY_STALE_REFRESH_QUEUED",
                    "executedProfitFactor": 0.0145,
                    "shadowProfitFactor": 0.7055,
                    "quarantineCount": 45,
                    "retuneTotal": 6,
                    "retuneRed": 3,
                    "retuneYellow": 2,
                },
                "topLossSources": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "profitFactor": 0.3956,
                    "winRatePct": 19.35,
                    "realizedPnl": -58.0649,
                }],
                "retuneSources": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                }],
                "copyTradingReview": {
                    "active": True,
                    "status": "COPY_TRADING_RETUNE_REQUIRED",
                    "summary": "Agent 已生成跟单重调方案。",
                    "bestExperimentKey": "copy_archive_all_markets_v1",
                    "iterationPlan": {
                        "completedByAgent": True,
                        "candidateVariants": [{"key": "copy_archive_all_market_whitelist_v2"}],
                    },
                },
                "copyRetuneSources": [{
                    "experimentKey": "copy_archive_all_markets_v1",
                    "routeFamily": "copy_archive",
                }],
            }
        }
        iteration = daily_review.daily_iteration_review(
            {"date": "2026-05-01", "closedTrades": 2, "netUSC": 3.54},
            [],
            poly,
            {"requiresCodexReview": False},
            5,
        )
        codex = daily_review.codex_review_queue(
            {"date": "2026-05-01", "closedTrades": 2, "netUSC": 3.54, "requiresReview": False},
            [],
            [],
            {},
            {},
            {},
            {"workerStatus": "OK"},
            {"requiresCodexReview": False},
            iteration,
        )

        self.assertEqual(iteration["status"], "REVIEW_COMPLETE_NO_CODE_CHANGE")
        self.assertFalse(iteration["codexFollowupRequired"])
        self.assertEqual(iteration["strategyIterationQueue"][0]["status"], "RETUNE_PLAN_READY_STALE_REFRESH_QUEUED")
        self.assertEqual(iteration["strategyIterationQueue"][1]["status"], "RETUNE_SPEC_READY_STALE_REFRESH_QUEUED")
        self.assertTrue(iteration["strategyIterationQueue"][1]["completedByAgent"])
        self.assertFalse(codex["required"])

    def test_completion_report_explains_finished_todos_and_recommendations(self):
        poly = {
            "dailyReview": {
                "summary": {
                    "lossQuarantine": True,
                    "executedProfitFactor": 0.0145,
                    "shadowProfitFactor": 0.7055,
                    "quarantineCount": 45,
                },
                "topLossSources": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "profitFactor": 0.3956,
                    "winRatePct": 19.35,
                    "realizedPnl": -58.0649,
                }],
            }
        }
        param_status = {
            "tasks": [{
                "candidateId": "BB_Triple_USDJPYc_bb_outer_band_strict_v2",
                "routeKey": "BB_Triple",
                "symbol": "USDJPYc",
                "status": "PARSED_AGENT_ARTIFACTS",
                "score": -7.745,
            }]
        }
        param_results = {
            "results": [{
                "candidateId": "BB_Triple_USDJPYc_bb_outer_band_strict_v2",
                "grade": "C",
                "promotionReadiness": "NEEDS_MORE_EVIDENCE",
                "metrics": {
                    "reportExists": True,
                    "parseStatus": "PARSED_AGENT_ARTIFACTS",
                    "closedTrades": 0,
                    "sampleStatus": "NO_TRADES_IN_TEST_WINDOW",
                },
            }]
        }
        iteration = {"iterationRequired": True}

        report = daily_review.build_completion_report(
            "2026-05-01",
            {"closedTrades": 2, "netUSC": 3.54, "requiresReview": False},
            param_status,
            param_results,
            [{"candidateId": "MA_Cross_USDJPYc_ma_slower_confirmation"}],
            [],
            poly,
            iteration,
        )

        self.assertEqual(report["status"], "ITERATION_REQUIRED")
        self.assertEqual(report["summary"]["testerParsedCount"], 1)
        self.assertEqual(report["summary"]["testerNoTradeCount"], 1)
        self.assertGreaterEqual(report["summary"]["recommendationCount"], 3)
        self.assertIn("不能作为升实盘证据", report["testerReports"][0]["effect"])
        self.assertTrue(any(item["scope"] == "Polymarket" for item in report["recommendations"]))
        self.assertFalse(report["safety"]["orderSendAllowed"])

    def test_daily_closeout_window_keeps_todos_on_same_local_day(self):
        now = datetime.fromisoformat("2026-05-02T00:25:00+09:00")
        plan = daily_review.tester_window_plan(now)

        self.assertTrue(plan["openNow"])
        self.assertTrue(plan["dueToday"])
        self.assertEqual(plan["nextWindowLabel"], "2026-05-02 00:00-02:30 JST")

    def test_auto_tester_guard_allows_daily_closeout_window(self):
        now = datetime.fromisoformat("2026-05-01T15:25:00+00:00")
        window = auto_tester_guard.regular_tester_window(now)

        self.assertTrue(window["ok"])
        self.assertEqual(window["blockers"], [])
        self.assertIn("Daily closeout 00:00-02:30 JST", window["windowLabel"])

    def test_tester_guard_accepts_wine_archive_report_paths(self):
        path = auto_tester_guard.path_from_tester_text(
            r"Z:\Users\bowen\Desktop\Quard\QuantGodBackend\archive\param-lab\runs\run\reports\EURUSDc\x.html"
        )

        self.assertEqual(
            str(path),
            "/Users/bowen/Desktop/Quard/QuantGodBackend/archive/param-lab/runs/run/reports/EURUSDc/x.html",
        )

    def test_tester_guard_remaps_legacy_monorepo_archive_path_after_split(self):
        repo_root = Path("/Users/bowen/Desktop/Quard/QuantGodBackend")
        path = auto_tester_guard.path_from_tester_text(
            r"Z:\Users\bowen\Desktop\Quard\\" + "Quant" + r"God\archive\param-lab\runs\run\reports\EURUSDc\x.html"
        )

        self.assertEqual(
            str(auto_tester_guard.normalize_repo_archive_path(path, repo_root)),
            "/Users/bowen/Desktop/Quard/QuantGodBackend/archive/param-lab/runs/run/reports/EURUSDc/x.html",
        )

    def test_auto_tester_retry_allows_fixed_missing_tester_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "run" / "configs" / "x.ini"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "[Common]\nLogin=186054398\nServer=HFMarketsGlobal-Live12\n\n[Tester]\nExpert=QuantGod_MultiStrategy.ex5\n",
                encoding="ascii",
            )
            status_path = root / "run" / "QuantGod_ParamLabStatus.json"
            status_path.write_text(json.dumps({
                "taskStatus": [{
                    "candidateId": "MA_Cross_EURUSDc_ma_control_tight_exit",
                    "configPath": str(config_path),
                }]
            }), encoding="utf-8")
            scheduler = {
                "selectedTasks": [{
                    "candidateId": "MA_Cross_EURUSDc_ma_control_tight_exit",
                    "routeKey": "MA_Cross",
                    "strategy": "MA_Cross",
                    "variant": "ma_control_tight_exit",
                }]
            }
            recovery = {
                "candidateDrilldown": [{
                    "candidateId": "MA_Cross_EURUSDc_ma_control_tight_exit",
                    "riskLevel": "red",
                    "riskReason": "terminal_nonzero",
                    "latestStatusPath": str(status_path),
                }]
            }

            effective, controls = auto_tester_window.apply_executor_controls(
                scheduler=scheduler,
                recovery=recovery,
                budget_policy={"defaultRouteBudget": 1},
                max_tasks=1,
                enforce_retry_drilldown=True,
                enforce_budget=True,
            )

        self.assertEqual(controls["redSkippedCount"], 0)
        self.assertEqual(len(effective["selectedTasks"]), 1)
        self.assertEqual(effective["selectedTasks"][0]["retryOverride"], "PREVIOUS_TESTER_CONFIG_MISSING_TESTER_LOGIN_FIXED")

    def test_polymarket_global_loss_copy_explains_risk_isolation(self):
        state, action, risk, next_test = poly_governance.classify_decision(
            92.0,
            False,
            ["SIM_SAMPLE_LT_MIN"],
            ["GLOBAL_LOSS_QUARANTINE", "EXECUTED_PF_BELOW_1"],
            type("Args", (), {"demote_score": 35.0, "keep_shadow_score": 58.0, "promotion_review_score": 78.0})(),
        )

        self.assertEqual(state, "QUARANTINE_NO_PROMOTION")
        self.assertEqual(risk, "high")
        self.assertIn("进入隔离", action)
        self.assertIn("风险隔离", next_test)
        self.assertIn("复盘亏损来源", next_test)
        self.assertNotIn("修复亏损来源", next_test)

    def test_polymarket_daily_review_builds_loss_todos_when_evidence_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            (runtime / "QuantGod_PolymarketResearch.json").write_text(json.dumps({
                "generatedAtIso": "2026-04-28T00:00:00+00:00",
                "summary": {
                    "executed": {"closed": 24, "winRatePct": 4.17, "profitFactor": 0.0145, "realizedPnl": -9.9841},
                    "shadow": {"closed": 383, "winRatePct": 36.29, "profitFactor": 0.7055, "realizedPnl": -159.3266},
                },
                "recentJournalGroups": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "marketScope": "sports",
                    "entryStatus": "live_blocked_shadow",
                    "signalSource": "autonomous",
                    "closed": 62,
                    "wins": 12,
                    "losses": 50,
                    "winRatePct": 19.35,
                    "profitFactor": 0.3956,
                    "realizedPnl": -58.0649,
                    "avgPnl": -0.9365,
                }],
                "recentExperimentGroups": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "closed": 62,
                    "wins": 12,
                    "losses": 50,
                    "winRatePct": 19.35,
                    "profitFactor": 0.3956,
                    "realizedPnl": -58.0649,
                    "avgPnl": -0.9365,
                }],
            }), encoding="utf-8")
            (runtime / "QuantGod_PolymarketAutoGovernance.json").write_text(json.dumps({
                "globalBlockers": ["GLOBAL_LOSS_QUARANTINE", "EXECUTED_PF_BELOW_1"],
                "summary": {"quarantine": 46, "autoCanaryEligible": 0},
            }), encoding="utf-8")
            (runtime / "QuantGod_PolymarketDryRunOutcomeWatcher.json").write_text(json.dumps({
                "summary": {"wouldExit": 4, "stopLoss": 2, "trailingExit": 2},
            }), encoding="utf-8")
            (runtime / "QuantGod_PolymarketExecutionGate.json").write_text(json.dumps({
                "summary": {"canBet": 0, "blocked": 24},
            }), encoding="utf-8")

            review = daily_review.polymarket_daily_review(runtime)

            self.assertTrue(review["summary"]["lossQuarantine"])
            self.assertEqual(review["summary"]["todoCount"], 4)
            self.assertEqual(review["actionQueue"][0]["type"], "POLY_LOSS_SOURCE_REVIEW")
            self.assertFalse(review["safety"]["walletWriteAllowed"])
            self.assertEqual(review["topLossSources"][0]["experimentKey"], "sports_edge_filter_shadow_v1")

    def test_polymarket_daily_review_hides_completed_fresh_retune_cycle(self):
        now = daily_review.utc_now().isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            (runtime / "QuantGod_PolymarketResearch.json").write_text(json.dumps({
                "generatedAtIso": now,
                "summary": {
                    "executed": {"closed": 24, "winRatePct": 4.17, "profitFactor": 0.0145, "realizedPnl": -9.9841},
                    "shadow": {"closed": 383, "winRatePct": 36.29, "profitFactor": 0.7055, "realizedPnl": -159.3266},
                },
                "recentJournalGroups": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "marketScope": "sports",
                    "entryStatus": "live_blocked_shadow",
                    "signalSource": "autonomous",
                    "closed": 62,
                    "wins": 12,
                    "losses": 50,
                    "winRatePct": 19.35,
                    "profitFactor": 0.3956,
                    "realizedPnl": -58.0649,
                    "avgPnl": -0.9365,
                }],
                "recentExperimentGroups": [{
                    "experimentKey": "sports_edge_filter_shadow_v1",
                    "closed": 62,
                    "wins": 12,
                    "losses": 50,
                    "winRatePct": 19.35,
                    "profitFactor": 0.3956,
                    "realizedPnl": -58.0649,
                    "avgPnl": -0.9365,
                }],
            }), encoding="utf-8")
            (runtime / "QuantGod_PolymarketRetunePlanner.json").write_text(json.dumps({
                "generatedAtIso": now,
                "status": "OK",
                "decision": "SHADOW_ONLY_RETUNE_NO_BETTING",
                "recommendationCounts": {"total": 3, "red": 1, "yellow": 2, "copyTrading": 1},
                "copyTradingReview": {
                    "status": "COPY_TRADING_RETUNE_REQUIRED",
                    "active": True,
                    "summary": "正在模拟跟单策略：样本 20，PF 0.98。",
                    "bestExperimentKey": "copy_archive_all_markets_v1",
                },
                "recommendations": [{
                    "experimentKey": "copy_archive_all_markets_v1",
                    "routeFamily": "copy_archive",
                    "marketScope": "all_markets",
                    "primaryAction": "RETUNE_SHADOW_ONLY",
                }],
            }), encoding="utf-8")
            (runtime / "QuantGod_PolymarketAutoGovernance.json").write_text(json.dumps({
                "generatedAt": now,
                "globalBlockers": ["GLOBAL_LOSS_QUARANTINE", "EXECUTED_PF_BELOW_1"],
                "summary": {"quarantine": 46, "autoCanaryEligible": 0},
            }), encoding="utf-8")
            (runtime / "QuantGod_PolymarketDryRunOutcomeWatcher.json").write_text(json.dumps({
                "generatedAtIso": now,
                "summary": {"wouldExit": 4, "stopLoss": 2, "trailingExit": 2},
            }), encoding="utf-8")
            (runtime / "QuantGod_PolymarketExecutionGate.json").write_text(json.dumps({
                "generatedAt": now,
                "summary": {"canBet": 0, "blocked": 24},
            }), encoding="utf-8")

            review = daily_review.polymarket_daily_review(runtime)

            self.assertEqual(review["status"], "DONE_HIDE_UNTIL_NEXT_REFRESH")
            self.assertTrue(review["summary"]["lossQuarantine"])
            self.assertEqual(review["summary"]["todoCount"], 0)
            self.assertGreaterEqual(review["summary"]["completedCount"], 4)
            self.assertEqual(review["summary"]["retuneCopyTrading"], 1)
            self.assertTrue(review["copyTradingReview"]["active"])
            self.assertEqual(review["copyRetuneSources"][0]["experimentKey"], "copy_archive_all_markets_v1")
            self.assertEqual(review["actionQueue"], [])
            self.assertEqual(review["completedActionQueue"][0]["state"], "DONE")

    def test_polymarket_research_replays_archived_snapshot_from_history_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "history.sqlite"
            con = __import__("sqlite3").connect(db_path)
            con.execute(
                "CREATE TABLE qd_polymarket_research_snapshots "
                "(generated_at TEXT, raw_json TEXT)"
            )
            con.execute(
                "INSERT INTO qd_polymarket_research_snapshots VALUES (?, ?)",
                (
                    "2026-05-01T18:06:59+00:00",
                    json.dumps({
                        "mode": "POLYMARKET_READ_ONLY_RESEARCH_BRIDGE",
                        "status": "OK",
                        "summary": {
                            "executed": {"closed": 0, "profitFactor": None},
                            "shadow": {"closed": 0, "profitFactor": None},
                        },
                    }),
                ),
            )
            con.execute(
                "INSERT INTO qd_polymarket_research_snapshots VALUES (?, ?)",
                (
                    "2026-04-28T10:57:30+00:00",
                    json.dumps({
                        "mode": "POLYMARKET_READ_ONLY_RESEARCH_BRIDGE",
                        "status": "OK",
                        "summary": {
                            "executed": {"closed": 24, "profitFactor": 0.0145},
                            "shadow": {"closed": 383, "profitFactor": 0.7055},
                        },
                        "source": {"dbPath": "D:/polymarket/copybot.db"},
                    }),
                ),
            )
            con.commit()
            con.close()

            snapshot = poly_research.build_snapshot(Path(tmp), db_path, 14, 5, skip_account_snapshot=True)

            self.assertEqual(snapshot["status"], "OK_ARCHIVED_SNAPSHOT")
            self.assertEqual(snapshot["summary"]["executed"]["closed"], 24)
            self.assertEqual(snapshot["summary"]["shadow"]["profitFactor"], 0.7055)
            self.assertTrue(snapshot["source"]["archiveReplay"])

    def test_daily_review_ledger_schema_upgrade_preserves_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "review.csv"
            ledger.write_text("A,B\nold_a,old_b\nnew_a,new_b,new_c\n", encoding="utf-8")

            daily_review.append_csv(ledger, {"A": "tail_a", "B": "tail_b", "C": "tail_c"}, ["A", "B", "C"])
            rows = list(__import__("csv").DictReader(ledger.read_text(encoding="utf-8").splitlines()))

            self.assertEqual(rows[0], {"A": "old_a", "B": "old_b", "C": ""})
            self.assertEqual(rows[1], {"A": "new_a", "B": "new_b", "C": ""})
            self.assertEqual(rows[2], {"A": "tail_a", "B": "tail_b", "C": "tail_c"})

    def test_daily_review_ledger_same_width_schema_change_does_not_shift_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "review.csv"
            ledger.write_text("A,B,C\nold_a,old_b,old_c\n", encoding="utf-8")

            daily_review.append_csv(ledger, {"A": "tail_a", "C": "tail_c", "D": "tail_d"}, ["A", "C", "D"])
            rows = list(__import__("csv").DictReader(ledger.read_text(encoding="utf-8").splitlines()))

            self.assertEqual(rows[0], {"A": "old_a", "C": "old_c", "D": ""})
            self.assertEqual(rows[1], {"A": "tail_a", "C": "tail_c", "D": "tail_d"})

    def test_autopilot_ledger_schema_upgrade_preserves_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "autopilot.csv"
            ledger.write_text("A,B\nold_a,old_b\nnew_a,new_b,new_c\n", encoding="utf-8")

            autopilot.append_csv(ledger, {"A": "tail_a", "B": "tail_b", "C": "tail_c"}, ["A", "B", "C"])
            rows = list(__import__("csv").DictReader(ledger.read_text(encoding="utf-8").splitlines()))

            self.assertEqual(rows[0], {"A": "old_a", "B": "old_b", "C": ""})
            self.assertEqual(rows[1], {"A": "new_a", "B": "new_b", "C": ""})
            self.assertEqual(rows[2], {"A": "tail_a", "B": "tail_b", "C": "tail_c"})

    def test_autopilot_ledger_same_width_schema_change_does_not_shift_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "autopilot.csv"
            ledger.write_text("A,B,C\nold_a,old_b,old_c\n", encoding="utf-8")

            autopilot.append_csv(ledger, {"A": "tail_a", "C": "tail_c", "D": "tail_d"}, ["A", "C", "D"])
            rows = list(__import__("csv").DictReader(ledger.read_text(encoding="utf-8").splitlines()))

            self.assertEqual(rows[0], {"A": "old_a", "C": "old_c", "D": ""})
            self.assertEqual(rows[1], {"A": "tail_a", "C": "tail_c", "D": "tail_d"})


if __name__ == "__main__":
    unittest.main()
