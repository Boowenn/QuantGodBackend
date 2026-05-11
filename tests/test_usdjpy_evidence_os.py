import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.agent_ops_health import build_agent_ops_health
from tools.strategy_ga.fitness import score_seed
from tools.strategy_ga.seed_generator import case_memory_seed_pool
from tools.strategy_json.schema import base_strategy_seed
from tools.usdjpy_evidence_os.execution_feedback import build_execution_feedback
from tools.usdjpy_evidence_os.parity import build_parity_report
from tools.usdjpy_evidence_os.report import build_evidence_os
from tools.usdjpy_evidence_os.telegram_gateway import (
    build_notification_event,
    collect_scheduled_events,
    dispatch_pending,
    enqueue_event,
    gateway_status,
)
from tools.usdjpy_strategy_backtest.report import ingest_klines, run_backtest


class USDJPYEvidenceOSTests(unittest.TestCase):
    def test_agent_ops_health_reports_agent_loop_heartbeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            missing = build_agent_ops_health(runtime_dir, repo_root=Path(__file__).resolve().parents[1], write=False)
            self.assertEqual(missing["agentV25Loop"]["status"], "WARN")

            heartbeat_dir = runtime_dir / "agent"
            heartbeat_dir.mkdir(parents=True)
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            (heartbeat_dir / "QuantGod_AgentV25LoopStatus.json").write_text(
                json.dumps(
                    {
                        "schema": "quantgod.agent_v25_loop_status.v1",
                        "generatedAtIso": now,
                        "lastHeartbeatAtIso": now,
                        "status": "COMPLETED",
                        "screenName": "quantgod-agent-v25",
                        "runtimeDir": str(runtime_dir),
                        "intervalSeconds": 300,
                        "sendTelegram": True,
                        "commandsAllowed": False,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (heartbeat_dir / "QuantGod_AgentV25SupervisorStatus.json").write_text(
                json.dumps(
                    {
                        "schema": "quantgod.agent_v25_supervisor_status.v1",
                        "generatedAtIso": now,
                        "action": "NOOP",
                        "reasonZh": "Agent v2.5 后台循环在线，心跳新鲜。",
                        "screenName": "quantgod-agent-v25",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            healthy = build_agent_ops_health(runtime_dir, repo_root=Path(__file__).resolve().parents[1], write=True)
            self.assertEqual(healthy["agentV25Loop"]["status"], "PASS", healthy["agentV25Loop"])
            self.assertEqual(healthy["agentV25Loop"]["supervisorAction"], "NOOP")
            self.assertEqual(healthy["checks"][0]["key"], "agentV25Loop")
            self.assertTrue((runtime_dir / "agent" / "QuantGod_AgentOpsHealth.json").exists())

    def test_execution_feedback_reads_live_mt5_files_dir_when_runtime_is_repo_local(self):
        old_mt5_files_dir = os.environ.get("QG_MT5_FILES_DIR")
        try:
            with tempfile.TemporaryDirectory() as runtime_tmp, tempfile.TemporaryDirectory() as mt5_tmp:
                runtime_dir = Path(runtime_tmp)
                mt5_files = Path(mt5_tmp)
                os.environ["QG_MT5_FILES_DIR"] = str(mt5_files)
                (mt5_files / "QuantGod_LiveExecutionFeedback.jsonl").write_text(
                    "\n".join(
                        [
                            '{"schema":"quantgod.live_execution_feedback.v1","feedbackId":"mt5-fill-001","eventType":"ORDER_FILL","symbol":"USDJPYc","side":"BUY","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","intentId":"pilot-live-001","expectedPrice":155.20,"fillPrice":155.21,"slippagePips":0.1,"latencyMs":140,"retcode":10009}',
                            '{"schema":"quantgod.live_execution_feedback.v1","feedbackId":"mt5-close-001","eventType":"ORDER_CLOSE","symbol":"USDJPYc","side":"SELL","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","intentId":"pilot-live-001","fillPrice":155.42,"slippagePips":0.0,"latencyMs":0,"profitR":0.8,"mfeR":1.1,"maeR":-0.2,"exitReason":"TP"}',
                        ]
                    ),
                    encoding="utf-8",
                )

                report = build_execution_feedback(runtime_dir, write=False)
                self.assertEqual(report["sampleCount"], 2)
                self.assertEqual(report["fieldCompleteness"]["status"], "PASS")
                self.assertEqual(report["fieldCompleteness"]["auditedRows"], 2)
                self.assertEqual(report["metrics"]["fillCount"], 2)
                self.assertEqual(report["recentFeedback"][0]["intentId"], "pilot-live-001")
        finally:
            if old_mt5_files_dir is None:
                os.environ.pop("QG_MT5_FILES_DIR", None)
            else:
                os.environ["QG_MT5_FILES_DIR"] = old_mt5_files_dir

    def test_parity_reads_live_mt5_rsi_diagnostics_when_runtime_is_repo_local(self):
        old_mt5_files_dir = os.environ.get("QG_MT5_FILES_DIR")
        try:
            with tempfile.TemporaryDirectory() as runtime_tmp, tempfile.TemporaryDirectory() as mt5_tmp:
                runtime_dir = Path(runtime_tmp)
                mt5_files = Path(mt5_tmp)
                os.environ["QG_MT5_FILES_DIR"] = str(mt5_files)
                live_dir = runtime_dir / "live"
                live_dir.mkdir(parents=True)
                (live_dir / "QuantGod_USDJPYLiveLoopStatus.json").write_text(
                    """
                    {
                      "topLiveEligiblePolicy": {
                        "strategy": "RSI_Reversal",
                        "direction": "LONG",
                        "entryMode": "OPPORTUNITY_ENTRY"
                      },
                      "safety": {
                        "orderSendAllowed": false,
                        "livePresetMutationAllowed": false
                      }
                    }
                    """,
                    encoding="utf-8",
                )
                (mt5_files / "QuantGod_USDJPYRsiEntryDiagnostics.json").write_text(
                    """
                    {
                      "schema": "quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1",
                      "symbol": "USDJPYc",
                      "strategy": "RSI_Reversal",
                      "direction": "LONG",
                      "state": "READY_BUY_SIGNAL",
                      "inputs": {
                        "PilotRsiTimeframe": "H1",
                        "PilotRsiPeriod": 2,
                        "PilotRsiOversold": 15,
                        "PilotRsiOverbought": 85,
                        "PilotRsiCrossbackThreshold": 0
                      },
                      "route": {
                        "timeframe": "H1",
                        "candidateEnabled": true,
                        "liveEnabled": true,
                        "inScope": true
                      },
                      "permissions": {
                        "liveMode": true,
                        "tradeAllowed": true,
                        "readOnlyMode": false
                      },
                      "guards": {
                        "sessionOpen": true,
                        "spreadAllowed": true,
                        "newsBlocked": false,
                        "cooldownActive": false,
                        "startupGuardActive": false,
                        "symbolPositions": 0,
                        "maxPositionsPerSymbol": 2
                      },
                      "rsi": {
                        "period": 2,
                        "oversold": 15,
                        "buyBandLevel": 15,
                        "crossbackThreshold": 0,
                        "signalReady": true,
                        "signalDirection": "BUY",
                        "evalCode": "SIGNAL_BUY"
                      }
                    }
                    """,
                    encoding="utf-8",
                )

                parity = build_parity_report(runtime_dir, write=True)
                self.assertEqual(parity["status"], "PARITY_PASS", parity)
                self.assertEqual(parity["promotionGate"]["status"], "PASS")
                self.assertTrue(
                    any(
                        check["name"] == "strategy_json_multi_strategy_coverage_matrix"
                        and check["status"] == "PASS"
                        for check in parity["checks"]
                    ),
                    parity["checks"],
                )
                self.assertEqual(parity["rsiDiagnosticsSource"]["type"], "standalone_file")
                self.assertIn(str(mt5_files), parity["rsiDiagnosticsSource"]["path"])
                self.assertTrue((runtime_dir / "QuantGod_USDJPYRsiEntryDiagnostics.json").exists())
                self.assertEqual(parity["deepParity"]["strategyJson"]["rsi"]["period"], 2.0)
        finally:
            if old_mt5_files_dir is None:
                os.environ.pop("QG_MT5_FILES_DIR", None)
            else:
                os.environ["QG_MT5_FILES_DIR"] = old_mt5_files_dir

    def test_parity_reads_embedded_dashboard_rsi_diagnostics_from_live_mt5_files_dir(self):
        old_mt5_files_dir = os.environ.get("QG_MT5_FILES_DIR")
        try:
            with tempfile.TemporaryDirectory() as runtime_tmp, tempfile.TemporaryDirectory() as mt5_tmp:
                runtime_dir = Path(runtime_tmp)
                mt5_files = Path(mt5_tmp)
                os.environ["QG_MT5_FILES_DIR"] = str(mt5_files)
                live_dir = runtime_dir / "live"
                live_dir.mkdir(parents=True)
                (live_dir / "QuantGod_USDJPYLiveLoopStatus.json").write_text(
                    """
                    {
                      "topLiveEligiblePolicy": {
                        "strategy": "RSI_Reversal",
                        "direction": "LONG",
                        "entryMode": "OPPORTUNITY_ENTRY"
                      },
                      "safety": {
                        "orderSendAllowed": false,
                        "livePresetMutationAllowed": false
                      }
                    }
                    """,
                    encoding="utf-8",
                )
                (mt5_files / "QuantGod_Dashboard.json").write_text(
                    """
                    {
                      "usdJpyRsiEntryDiagnostics": {
                        "schema": "quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1",
                        "symbol": "USDJPYc",
                        "strategy": "RSI_Reversal",
                        "direction": "LONG",
                        "state": "READY_BUY_SIGNAL",
                        "inputs": {
                          "PilotRsiTimeframe": "H1",
                          "PilotRsiPeriod": 2,
                          "PilotRsiOversold": 15,
                          "PilotRsiOverbought": 85,
                          "PilotRsiCrossbackThreshold": 0
                        },
                        "route": {
                          "timeframe": "H1",
                          "candidateEnabled": true,
                          "liveEnabled": true,
                          "inScope": true
                        },
                        "permissions": {
                          "liveMode": true,
                          "tradeAllowed": true,
                          "readOnlyMode": false
                        },
                        "guards": {
                          "sessionOpen": true,
                          "spreadAllowed": true,
                          "newsBlocked": false,
                          "cooldownActive": false,
                          "startupGuardActive": false,
                          "symbolPositions": 0,
                          "maxPositionsPerSymbol": 2
                        },
                        "rsi": {
                          "period": 2,
                          "oversold": 15,
                          "buyBandLevel": 15,
                          "crossbackThreshold": 0,
                          "signalReady": true,
                          "signalDirection": "BUY",
                          "evalCode": "SIGNAL_BUY"
                        }
                      }
                    }
                    """,
                    encoding="utf-8",
                )

                parity = build_parity_report(runtime_dir, write=True)
                self.assertEqual(parity["status"], "PARITY_PASS", parity)
                self.assertEqual(parity["promotionGate"]["status"], "PASS")
                self.assertEqual(parity["rsiDiagnosticsSource"]["type"], "dashboard_embedded")
                self.assertTrue((runtime_dir / "QuantGod_USDJPYRsiEntryDiagnostics.json").exists())
        finally:
            if old_mt5_files_dir is None:
                os.environ.pop("QG_MT5_FILES_DIR", None)
            else:
                os.environ["QG_MT5_FILES_DIR"] = old_mt5_files_dir

    def test_ingest_snapshot_backtest_and_evidence_os_write_audit_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            snapshot = runtime_dir / "QuantGod_MT5RuntimeSnapshot_USDJPYc.json"
            snapshot.write_text(
                """
                {
                  "symbol": "USDJPYc",
                  "kline_h1": [
                    {"timeIso":"2026-05-07T00:00:00Z","open":155.1,"high":155.2,"low":155.0,"close":155.15,"volume":100},
                    {"timeIso":"2026-05-07T01:00:00Z","open":155.15,"high":155.3,"low":155.1,"close":155.25,"volume":100}
                  ],
                  "kline_m15": [
                    {"timeIso":"2026-05-07T00:00:00Z","open":155.1,"high":155.12,"low":155.0,"close":155.1,"volume":25}
                  ],
                  "kline_h4": [
                    {"timeIso":"2026-05-07T00:00:00Z","open":155.1,"high":155.4,"low":155.0,"close":155.3,"volume":400}
                  ],
                  "kline_d1": [
                    {"timeIso":"2026-05-07T00:00:00Z","open":155.1,"high":155.8,"low":154.9,"close":155.5,"volume":1000}
                  ]
                }
                """,
                encoding="utf-8",
            )

            ingest = ingest_klines(runtime_dir)
            self.assertTrue(ingest["sourceFound"])
            self.assertEqual(ingest["insertedOrUpdated"]["H1"], 2)

            backtest = run_backtest(runtime_dir, write=True)
            self.assertTrue(backtest["ok"], backtest)
            self.assertIn("multiTimeframe", backtest)
            self.assertEqual(backtest["multiTimeframe"]["contexts"]["H4"]["barCount"], 1)

            (runtime_dir / "QuantGod_RuntimeTradeEvents.jsonl").write_text(
                "\n".join(
                    [
                        '{"generatedAt":"2026-05-07T01:00:01Z","eventType":"ORDER_FILL","symbol":"USDJPYc","price":155.24,"volume":0.05,"retcode":10009,"policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","expectedPrice":155.23,"latencyMs":420,"profitR":0.2}',
                        '{"generatedAt":"2026-05-07T02:00:01Z","eventType":"ORDER_REJECT","symbol":"USDJPYc","price":155.40,"volume":0.05,"retcode":10030,"policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal"}',
                    ]
                ),
                encoding="utf-8",
            )
            (runtime_dir / "QuantGod_LiveExecutionFeedback.jsonl").write_text(
                "\n".join(
                    [
                        '{"schema":"quantgod.live_execution_feedback.v1","feedbackId":"send-001","eventType":"ORDER_ACCEPTED","symbol":"USDJPYc","side":"BUY","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","intentId":"pilot-001","expectedPrice":155.23,"fillPrice":155.24,"slippagePips":0.1,"spreadAtEntry":0.3,"latencyMs":110,"retcode":10009}',
                        '{"schema":"quantgod.live_execution_feedback.v1","feedbackId":"send-002","eventType":"ORDER_REJECTED","symbol":"USDJPYc","side":"BUY","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","intentId":"pilot-002","expectedPrice":155.40,"fillPrice":0,"slippagePips":0,"spreadAtEntry":0.4,"latencyMs":95,"retcode":10030}',
                    ]
                ),
                encoding="utf-8",
            )
            (runtime_dir / "QuantGod_LiveExecutionFeedbackHistory.jsonl").write_text(
                "\n".join(
                    [
                        '{"schema":"quantgod.live_execution_feedback.v1","feedbackId":"history-001","eventType":"ORDER_FILL","symbol":"USDJPYc","side":"BUY","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","intentId":"history-001","dealTicket":1,"fillPrice":155.24,"slippagePips":0.1,"latencyMs":0,"profitR":0.0}',
                        '{"schema":"quantgod.live_execution_feedback.v1","feedbackId":"history-002","eventType":"ORDER_CLOSE","symbol":"USDJPYc","side":"SELL","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","intentId":"history-002","dealTicket":2,"fillPrice":155.42,"slippagePips":0.0,"latencyMs":0,"profitR":0.45,"mfeR":0.7,"maeR":-0.2,"exitReason":"HISTORY_EXIT"}',
                    ]
                ),
                encoding="utf-8",
            )
            evidence = build_evidence_os(runtime_dir, write=True)
            self.assertTrue(evidence["ok"])
            self.assertIn("parity", evidence)
            self.assertIn("executionFeedback", evidence)
            self.assertIn("caseMemory", evidence)
            self.assertEqual(evidence["executionFeedback"]["metrics"]["acceptedCount"], 1)
            self.assertEqual(evidence["executionFeedback"]["metrics"]["fillCount"], 3)
            self.assertEqual(evidence["executionFeedback"]["metrics"]["rejectCount"], 2)
            self.assertIn("dominantRejectReason", evidence["executionFeedback"]["metrics"])
            sources = {row["source"] for row in evidence["executionFeedback"]["recentFeedback"]}
            self.assertIn("QuantGod_LiveExecutionFeedback.jsonl", sources)
            self.assertIn("QuantGod_LiveExecutionFeedbackHistory.jsonl", sources)
            self.assertIn("qualityGates", evidence["executionFeedback"])
            self.assertIn("promotionGate", evidence["executionFeedback"])
            self.assertIn("fieldCompleteness", evidence["executionFeedback"])
            self.assertEqual(evidence["executionFeedback"]["fieldCompleteness"]["status"], "PASS")
            self.assertEqual(evidence["executionFeedback"]["metrics"]["fieldCompletenessStatus"], "PASS")
            self.assertEqual(evidence["executionFeedback"]["recentFeedback"][0]["intentId"], "pilot-001")
            self.assertIn(evidence["executionFeedback"]["promotionGate"]["status"], {"PASS", "WATCH", "BLOCKED"})
            self.assertIn("parityDimensions", evidence["parity"])
            self.assertFalse(evidence["safety"]["orderSendAllowed"])
            self.assertTrue((runtime_dir / "evidence_os" / "QuantGod_StrategyParityReport.json").exists())

    def test_execution_quality_feeds_case_memory_and_ga_penalty(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            run_backtest(runtime_dir, write=True)
            (runtime_dir / "QuantGod_USDJPYRsiEntryDiagnostics.json").write_text(
                """
                {
                  "schema": "quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1",
                  "symbol": "USDJPYc",
                  "strategy": "RSI_Reversal",
                  "direction": "LONG",
                  "state": "READY_BUY_SIGNAL",
                  "route": {"timeframe": "H1", "candidateEnabled": true, "liveEnabled": true},
                  "guards": {"sessionOpen": true, "spreadAllowed": true, "newsBlocked": false},
                  "rsi": {
                    "period": 14,
                    "oversold": 34,
                    "signalReady": true,
                    "signalDirection": "LONG",
                    "evalCode": "READY"
                  }
                }
                """,
                encoding="utf-8",
            )
            (runtime_dir / "QuantGod_LiveExecutionFeedback.jsonl").write_text(
                "\n".join(
                    [
                        '{"feedbackId":"ack-1","eventType":"ORDER_ACCEPTED","symbol":"USDJPYc","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","expectedPrice":155.10,"latencyMs":2600}',
                        '{"feedbackId":"ack-2","eventType":"ORDER_ACCEPTED","symbol":"USDJPYc","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","expectedPrice":155.11,"latencyMs":2800}',
                        '{"feedbackId":"ack-3","eventType":"ORDER_ACCEPTED","symbol":"USDJPYc","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","expectedPrice":155.12,"latencyMs":3000}',
                        '{"feedbackId":"rej-1","eventType":"ORDER_REJECTED","symbol":"USDJPYc","policyId":"USDJPY_LIVE_LOOP","strategyId":"RSI_Reversal","retcode":10030,"latencyMs":2100}',
                        '{"feedbackId":"fill-1","eventType":"ORDER_FILL","symbol":"USDJPYc","policyId":"EVIDENCE_MISSING","strategyId":"RSI_Reversal","expectedPrice":155.00,"fillPrice":155.03,"slippagePips":3.0,"latencyMs":2400}',
                    ]
                ),
                encoding="utf-8",
            )

            evidence = build_evidence_os(runtime_dir, write=True)
            metrics = evidence["executionFeedback"]["metrics"]
            self.assertEqual(metrics["acceptedWithoutFillCount"], 3)
            self.assertGreater(metrics["avgAbsSlippagePips"], 0.8)
            self.assertGreater(metrics["avgLatencyMs"], 1500)
            self.assertEqual(metrics["policyMismatchCount"], 1)
            self.assertEqual(evidence["executionFeedback"]["fieldCompleteness"]["status"], "BLOCKED")
            self.assertGreater(evidence["executionFeedback"]["metrics"]["coreMissingFieldCount"], 0)
            self.assertIn("intentId", evidence["executionFeedback"]["fieldCompleteness"]["missingCounts"])
            self.assertEqual(evidence["executionFeedback"]["promotionGate"]["status"], "BLOCKED")
            self.assertFalse(evidence["executionFeedback"]["promotionGate"]["promotionAllowed"])
            self.assertGreaterEqual(len(evidence["executionFeedback"]["caseMemoryTriggers"]), 1)

            cases = evidence["caseMemory"]
            self.assertIn("EXECUTION_FEEDBACK_SCHEMA_GAP", cases["caseTypeCounts"])
            self.assertIn("EXECUTION_SLIPPAGE", cases["caseTypeCounts"])
            self.assertIn("EXECUTION_LATENCY", cases["caseTypeCounts"])
            self.assertIn("POLICY_MISMATCH", cases["caseTypeCounts"])
            self.assertIn("gaSeedHints", cases)
            self.assertGreaterEqual(cases["caseMemoryToGA"]["queuedHintCount"], 1)
            hints = {row["mutationHint"] for row in cases["gaSeedHints"]}
            self.assertIn("tighten_execution_filter", hints)
            seeds = case_memory_seed_pool(runtime_dir)
            self.assertTrue(seeds)
            self.assertTrue(any(seed.get("source") == "CASE_MEMORY" for seed in seeds))
            self.assertTrue(any(seed.get("casePriority") == "HIGH" for seed in seeds))

            score = score_seed(base_strategy_seed("GA-EXECUTION-QUALITY"), runtime_dir)
            self.assertGreater(score["executionFeedback"]["penalty"], 0.5)
            self.assertEqual(score["executionFeedback"]["promotionGateStatus"], "BLOCKED")
            self.assertGreater(score["caseMemory"]["penalty"], 0.0)
            self.assertEqual(score["parity"]["promotionGateStatus"], "BLOCKED")
            self.assertGreaterEqual(score["parity"]["penalty"], 0.65)

    def test_parity_mismatch_blocks_promotion_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            run_backtest(runtime_dir, write=True)
            live_dir = runtime_dir / "live"
            live_dir.mkdir(parents=True)
            (live_dir / "QuantGod_USDJPYLiveLoopStatus.json").write_text(
                """
                {
                  "topLiveEligiblePolicy": {
                    "strategy": "RSI_Reversal",
                    "direction": "LONG",
                    "entryMode": "OPPORTUNITY_ENTRY"
                  },
                  "safety": {
                    "orderSendAllowed": false,
                    "livePresetMutationAllowed": false
                  }
                }
                """,
                encoding="utf-8",
            )
            (runtime_dir / "QuantGod_USDJPYRsiEntryDiagnostics.json").write_text(
                """
                {
                  "schema": "quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1",
                  "symbol": "USDJPYc",
                  "strategy": "RSI_Reversal",
                  "direction": "SHORT",
                  "route": {"timeframe": "H1", "candidateEnabled": true, "liveEnabled": true},
                  "guards": {"sessionOpen": true, "spreadAllowed": true, "newsBlocked": false},
                  "rsi": {
                    "period": 21,
                    "oversold": 34,
                    "signalReady": true,
                    "signalDirection": "SHORT",
                    "evalCode": "READY"
                  }
                }
                """,
                encoding="utf-8",
            )

            parity = build_parity_report(runtime_dir, write=True)
            self.assertEqual(parity["status"], "PARITY_FAIL")
            self.assertEqual(parity["promotionGate"]["status"], "BLOCKED")
            self.assertFalse(parity["promotionGate"]["promotionAllowed"])
            blocker_names = {row["name"] for row in parity["promotionGate"]["blockers"]}
            self.assertIn("strategy_json_vs_mql5_rsi_diagnostics", blocker_names)

    def test_deep_parity_matrix_passes_when_strategy_replay_and_ea_align(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            run_backtest(runtime_dir, write=True)
            replay_dir = runtime_dir / "replay" / "usdjpy"
            replay_dir.mkdir(parents=True)
            (replay_dir / "QuantGod_USDJPYBarReplayReport.json").write_text(
                """
                {
                  "schema": "quantgod.usdjpy_bar_replay.report.v1",
                  "symbol": "USDJPYc",
                  "causalReplay": {
                    "posteriorMayAffectTrigger": false,
                    "posteriorUsedForScoringOnly": true
                  },
                  "entryComparison": {
                    "causalReplay": {
                      "posteriorMayAffectTrigger": false,
                      "hardGatesNeverRelaxed": ["runtime", "fastlane", "highImpactNews", "spread", "session", "cooldown", "startup", "capacity"],
                      "ordinaryNewsBlocksLive": false
                    },
                    "events": {
                      "current": [
                        {
                          "allowed": true,
                          "hardGatePass": true,
                          "tacticalGatePass": true,
                          "hardBlockers": [],
                          "tacticalBlockers": [],
                          "posteriorUsedForTrigger": false
                        }
                      ]
                    }
                  }
                }
                """,
                encoding="utf-8",
            )
            live_dir = runtime_dir / "live"
            live_dir.mkdir(parents=True)
            (live_dir / "QuantGod_USDJPYLiveLoopStatus.json").write_text(
                """
                {
                  "topLiveEligiblePolicy": {
                    "strategy": "RSI_Reversal",
                    "direction": "LONG",
                    "entryMode": "OPPORTUNITY_ENTRY"
                  },
                  "safety": {
                    "orderSendAllowed": false,
                    "livePresetMutationAllowed": false
                  }
                }
                """,
                encoding="utf-8",
            )
            (runtime_dir / "QuantGod_USDJPYRsiEntryDiagnostics.json").write_text(
                """
                {
                  "schema": "quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1",
                  "symbol": "USDJPYc",
                  "strategy": "RSI_Reversal",
                  "direction": "LONG",
                  "state": "READY_BUY_SIGNAL",
                  "route": {
                    "timeframe": "H1",
                    "candidateEnabled": true,
                    "liveEnabled": true,
                    "inScope": true
                  },
                  "permissions": {
                    "liveMode": true,
                    "tradeAllowed": true,
                    "readOnlyMode": false
                  },
                  "guards": {
                    "sessionOpen": true,
                    "spreadAllowed": true,
                    "newsBlocked": false,
                    "cooldownActive": false,
                    "startupGuardActive": false,
                    "symbolPositions": 0,
                    "maxPositionsPerSymbol": 2
                  },
                  "rsi": {
                    "period": 14,
                    "oversold": 34,
                    "crossbackThreshold": 0.8,
                    "signalReady": true,
                    "signalDirection": "LONG",
                    "evalCode": "READY"
                  }
                }
                """,
                encoding="utf-8",
            )

            parity = build_parity_report(runtime_dir, write=True)
            self.assertEqual(parity["status"], "PARITY_PASS")
            self.assertEqual(parity["promotionGate"]["status"], "PASS")
            self.assertEqual(parity["deepParity"]["status"], "PASS")
            check_by_name = {row["name"]: row for row in parity["checks"]}
            self.assertEqual(check_by_name["strategy_json_python_replay_mql5_gate_matrix"]["status"], "PASS")
            self.assertIn("pythonReplay", parity["deepParity"])
            self.assertIn("mql5Ea", parity["deepParity"])

    def test_parity_auto_syncs_strategy_json_and_python_replay_from_live_ea_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            live_dir = runtime_dir / "live"
            live_dir.mkdir(parents=True)
            (live_dir / "QuantGod_USDJPYLiveLoopStatus.json").write_text(
                """
                {
                  "topLiveEligiblePolicy": {
                    "strategy": "RSI_Reversal",
                    "direction": "LONG",
                    "entryMode": "OPPORTUNITY_ENTRY"
                  },
                  "safety": {
                    "orderSendAllowed": false,
                    "livePresetMutationAllowed": false
                  }
                }
                """,
                encoding="utf-8",
            )
            (runtime_dir / "QuantGod_USDJPYRsiEntryDiagnostics.json").write_text(
                """
                {
                  "schema": "quantgod.mt5.usdjpy_rsi_entry_diagnostics.v1",
                  "symbol": "USDJPYc",
                  "strategy": "RSI_Reversal",
                  "direction": "LONG",
                  "state": "READY_BUY_SIGNAL",
                  "inputs": {
                    "PilotRsiTimeframe": "H1",
                    "PilotRsiPeriod": 2,
                    "PilotRsiOversold": 15,
                    "PilotRsiOverbought": 85,
                    "PilotRsiCrossbackThreshold": 0
                  },
                  "route": {
                    "timeframe": "H1",
                    "candidateEnabled": true,
                    "liveEnabled": true,
                    "inScope": true
                  },
                  "permissions": {
                    "liveMode": true,
                    "tradeAllowed": true,
                    "readOnlyMode": false
                  },
                  "guards": {
                    "sessionOpen": true,
                    "spreadAllowed": true,
                    "newsBlocked": false,
                    "cooldownActive": false,
                    "startupGuardActive": false,
                    "symbolPositions": 0,
                    "maxPositionsPerSymbol": 2
                  },
                  "rsi": {
                    "period": 2,
                    "oversold": 15,
                    "buyBandLevel": 15,
                    "crossbackThreshold": 0,
                    "signalReady": true,
                    "signalDirection": "BUY",
                    "evalCode": "SIGNAL_BUY"
                  }
                }
                """,
                encoding="utf-8",
            )

            parity = build_parity_report(runtime_dir, write=True)
            self.assertEqual(parity["status"], "PARITY_PASS", parity)
            self.assertEqual(parity["promotionGate"]["status"], "PASS")
            self.assertEqual(parity["evidenceSync"]["strategyJsonBacktest"], "WRITTEN")
            self.assertEqual(parity["evidenceSync"]["pythonReplay"], "WRITTEN")
            self.assertTrue((runtime_dir / "backtest" / "QuantGod_StrategyBacktestReport.json").exists())
            self.assertTrue((runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYBarReplayReport.json").exists())
            self.assertEqual(parity["deepParity"]["strategyJson"]["rsi"]["period"], 2.0)
            self.assertEqual(parity["deepParity"]["strategyJson"]["rsi"]["buyBand"], 15.0)
            self.assertEqual(parity["deepParity"]["mql5Ea"]["rsi"]["signalDirection"], "BUY")
            self.assertEqual(parity["deepParity"]["hardMismatches"], [])

    def test_independent_telegram_gateway_queues_dedupes_and_keeps_dry_run_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            event = build_notification_event(
                "unit_test",
                "EVIDENCE_OS_TEST",
                "INFO",
                "【QuantGod 测试】Gateway 只做中文 push，不接收交易命令。",
            )
            first = enqueue_event(runtime_dir, event)
            second = enqueue_event(runtime_dir, event)
            self.assertEqual(first["queued"], 1)
            self.assertEqual(second["queued"], 0)
            dispatched = dispatch_pending(runtime_dir, send=False)
            self.assertEqual(dispatched["dispatchedCount"], 1)
            self.assertEqual(dispatched["pendingCount"], 1)
            status = gateway_status(runtime_dir)
            self.assertEqual(status["pendingCount"], 1)
            self.assertEqual(status["deliveredCount"], 0)
            self.assertGreaterEqual(status["ledgerCount"], 1)
            self.assertFalse(status["commandsAllowed"])
            self.assertTrue((runtime_dir / "notifications" / "QuantGod_TelegramGatewayLedger.jsonl").exists())

    def test_telegram_gateway_collects_scheduled_operator_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            (runtime_dir / "QuantGod_PolymarketRetunePlanner.json").write_text(
                """
                {
                  "status": "OK",
                  "decision": "SHADOW_ONLY_RETUNE_NO_BETTING",
                  "recommendationCounts": {"red": 1, "yellow": 2, "green": 0, "gray": 0},
                  "copyTradingReview": {
                    "status": "COPY_TRADING_RETUNE_REQUIRED",
                    "agentRetuneStatus": "COMPLETED_BY_AGENT",
                    "operatorStatusLabel": "仍在隔离",
                    "completedByAgent": true,
                    "autoAppliedByAgent": true,
                    "summary": "跟单策略已由 Agent 自动生成 retune plan；继续 shadow-only。",
                    "bestMetrics": {"source": "sports", "closed": 179, "profitFactor": 0.9821, "winRatePct": 49.72},
                    "capitalSimulation": {"cashScaledUSDC": "-$0.06", "ledgerNetUSDC": "-$4.23"},
                    "nextActions": ["继续模拟重调，不连接真实钱包"]
                  }
                }
                """,
                encoding="utf-8",
            )

            status = collect_scheduled_events(runtime_dir, repo_root=Path(__file__).resolve().parents[1], refresh=True)

            self.assertTrue(status["scheduledCollector"])
            topics = {row.get("topic") for row in status["collectedEvents"]}
            self.assertIn("DAILY_AUTOPILOT_V2_REPORT", topics)
            self.assertIn("GA_EVOLUTION_REPORT", topics)
            self.assertIn("USDJPY_AUTONOMOUS_AGENT_REPORT", topics)
            self.assertIn("POLYMARKET_RETUNE_REPORT", topics)
            queued_status = gateway_status(runtime_dir)
            self.assertGreaterEqual(queued_status["queuedCount"], 4)
            self.assertGreaterEqual(queued_status["pendingCount"], 4)
            queue_text = (runtime_dir / "notifications" / "QuantGod_NotificationEventQueue.jsonl").read_text(encoding="utf-8")
            self.assertIn("POLYMARKET_RETUNE_REPORT", queue_text)
            self.assertIn("不连接真实钱包", queue_text)
            second = collect_scheduled_events(runtime_dir, repo_root=Path(__file__).resolve().parents[1], refresh=True)
            queued_again = sum(int(row.get("queued") or 0) for row in second["collectedEvents"])
            self.assertEqual(queued_again, 0)

    def test_ga_fitness_consumes_parity_execution_and_case_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            run_backtest(runtime_dir, write=True)
            build_evidence_os(runtime_dir, write=True)
            score = score_seed(base_strategy_seed("GA-EVIDENCE-OS"), runtime_dir)
            self.assertIn("parity", score)
            self.assertIn("executionFeedback", score)
            self.assertIn("caseMemory", score)
            self.assertIn("evidencePenalty", score)


if __name__ == "__main__":
    unittest.main()
