import csv, json, tempfile, unittest
from pathlib import Path
from tools.entry_trigger_lab.data_loader import sample_runtime
from tools.entry_trigger_lab.trigger_engine import build_trigger_plan
from tools.entry_trigger_lab.telegram_text import build_telegram_text

class EntryTriggerLabTests(unittest.TestCase):
    def test_builds_read_only_trigger_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); sample_runtime(runtime,["USDJPYc"],overwrite=True)
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG","SHORT"])
            self.assertEqual(plan["schema"],"quantgod.entry_trigger_lab.v1")
            self.assertFalse(plan["safety"]["orderSendAllowed"])
            self.assertFalse(plan["safety"]["brokerExecutionAllowed"])
            self.assertEqual(len(plan["decisions"]),2)
    def test_degraded_fastlane_blocks_trigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); sample_runtime(runtime,["USDJPYc"],overwrite=True)
            quality=runtime/"quality"/"QuantGod_MT5FastLaneQuality.json"
            payload=json.loads(quality.read_text(encoding="utf-8")); payload["symbols"]["USDJPYc"]["quality"]="DEGRADED"
            quality.write_text(json.dumps(payload), encoding="utf-8")
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertEqual(decision["state"],"BLOCKED")
            self.assertFalse(decision["confirmations"]["快通道质量通过"])
    def test_fastlane_symbol_list_shape_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); sample_runtime(runtime,["USDJPYc"],overwrite=True)
            quality=runtime/"quality"/"QuantGod_MT5FastLaneQuality.json"
            payload=json.loads(quality.read_text(encoding="utf-8"))
            payload["quality"]="FAST"
            payload["symbols"]=[{"symbol":"USDJPYc","quality":"FAST","heartbeatFresh":True,"tickFresh":True,"indicatorFresh":True,"spreadOk":True}]
            quality.write_text(json.dumps(payload), encoding="utf-8")
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertTrue(decision["confirmations"]["快通道质量存在"])
            self.assertTrue(decision["confirmations"]["快通道质量通过"])
            self.assertNotIn("缺少 MT5 快通道质量证据", "；".join(decision["reasons"]))
    def test_hfm_dashboard_and_empty_fastlane_exporter_are_usable_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); runtime.mkdir(parents=True, exist_ok=True)
            (runtime/"quality").mkdir(parents=True, exist_ok=True); (runtime/"adaptive").mkdir(parents=True, exist_ok=True)
            (runtime/"QuantGod_Dashboard.json").write_text(json.dumps({
                "watchlist":"USDJPYc",
                "runtime":{"tradeStatus":"READY","executionEnabled":True,"readOnlyMode":False,"tickAgeSeconds":0},
                "market":{"bid":155.92,"ask":155.95,"spread":3.0},
            }), encoding="utf-8")
            (runtime/"quality"/"QuantGod_MT5FastLaneQuality.json").write_text(json.dumps({
                "schema":"quantgod.mt5.fastlane.quality.v1",
                "heartbeatFound":False,
                "quality":"DEGRADED",
                "symbols":[{"symbol":"USDJPYc","quality":"DEGRADED","tickRows":0,"tickAgeSeconds":None,"indicatorAgeSeconds":None}],
            }), encoding="utf-8")
            (runtime/"adaptive"/"QuantGod_DynamicEntryGate.json").write_text(json.dumps({
                "entryGates":[{"symbol":"USDJPYc","direction":"LONG","passed":True,"state":"PASS"}],
            }), encoding="utf-8")
            (runtime/"ShadowCandidateOutcomeLedger.csv").write_text(
                "symbol,direction,scoreR,pips\n"
                "USDJPYc,LONG,0.42,4.2\n"
                "USDJPYc,LONG,0.27,2.7\n"
                "USDJPYc,LONG,0.13,1.3\n",
                encoding="utf-8",
            )
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertTrue(decision["confirmations"]["运行快照新鲜"])
            self.assertTrue(decision["confirmations"]["快通道质量通过"])
            self.assertEqual(decision["state"],"WAIT_TRIGGER_CONFIRMATION")

    def test_stale_degraded_fastlane_exporter_uses_fresh_dashboard_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); runtime.mkdir(parents=True, exist_ok=True)
            (runtime/"quality").mkdir(parents=True, exist_ok=True); (runtime/"adaptive").mkdir(parents=True, exist_ok=True)
            (runtime/"QuantGod_Dashboard.json").write_text(json.dumps({
                "watchlist":"USDJPYc",
                "runtime":{"tradeStatus":"READY","executionEnabled":True,"readOnlyMode":False,"tickAgeSeconds":2},
                "market":{"bid":155.92,"ask":155.95,"spread":3.0},
            }), encoding="utf-8")
            (runtime/"quality"/"QuantGod_MT5FastLaneQuality.json").write_text(json.dumps({
                "schema":"quantgod.mt5.fastlane.quality.v1",
                "heartbeatFound":True,
                "heartbeatFresh":False,
                "heartbeatAgeSeconds":120,
                "heartbeatFreshLimitSeconds":90,
                "quality":"DEGRADED",
                "symbols":[{
                    "symbol":"USDJPYc",
                    "quality":"DEGRADED",
                    "tickRows":3,
                    "tickAgeSeconds":2,
                    "indicatorAgeSeconds":39,
                    "checks":[
                        {"name":"tick_fast_lane","passed":False,"reason":"tick年龄=9秒"},
                        {"name":"indicator_lane","passed":False},
                        {"name":"tick_rows","passed":True},
                        {"name":"spread","passed":True},
                    ],
                }],
            }), encoding="utf-8")
            (runtime/"adaptive"/"QuantGod_DynamicEntryGate.json").write_text(json.dumps({
                "entryGates":[{"symbol":"USDJPYc","direction":"LONG","passed":True,"state":"PASS"}],
            }), encoding="utf-8")
            (runtime/"ShadowCandidateOutcomeLedger.csv").write_text(
                "symbol,direction,scoreR,pips\n"
                "USDJPYc,LONG,0.42,4.2\n"
                "USDJPYc,LONG,0.27,2.7\n"
                "USDJPYc,LONG,0.13,1.3\n",
                encoding="utf-8",
            )
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertTrue(decision["confirmations"]["快通道质量通过"])
            self.assertEqual(decision["state"],"WAIT_TRIGGER_CONFIRMATION")

    def test_candidate_outcome_ledger_fields_count_as_shadow_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); runtime.mkdir(parents=True, exist_ok=True)
            (runtime/"quality").mkdir(parents=True, exist_ok=True); (runtime/"adaptive").mkdir(parents=True, exist_ok=True)
            (runtime/"QuantGod_MT5RuntimeSnapshot_USDJPYc.json").write_text(json.dumps({"symbol":"USDJPYc","runtimeFresh":True,"fallback":False}), encoding="utf-8")
            (runtime/"quality"/"QuantGod_MT5FastLaneQuality.json").write_text(json.dumps({"symbols":[{"symbol":"USDJPYc","quality":"FAST","tickRows":3}]}), encoding="utf-8")
            (runtime/"adaptive"/"QuantGod_DynamicEntryGate.json").write_text(json.dumps({"entryGates":[{"symbol":"USDJPYc","passed":True}]}), encoding="utf-8")
            with (runtime/"QuantGod_ShadowCandidateOutcomeLedger.csv").open("w", encoding="utf-8", newline="") as fh:
                writer=csv.DictWriter(fh, fieldnames=["Symbol","CandidateDirection","LongClosePips","ShortClosePips"])
                writer.writeheader()
                writer.writerows([
                    {"Symbol":"USDJPYc","CandidateDirection":"BUY","LongClosePips":"2.1","ShortClosePips":"-2.1"},
                    {"Symbol":"USDJPYc","CandidateDirection":"BUY","LongClosePips":"1.3","ShortClosePips":"-1.3"},
                    {"Symbol":"USDJPYc","CandidateDirection":"BUY","LongClosePips":"0.8","ShortClosePips":"-0.8"},
                ])
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertTrue(decision["confirmations"]["影子样本未显示负期望"])
            self.assertEqual(decision["state"],"WAIT_TRIGGER_CONFIRMATION")
    def test_fastlane_symbol_dict_without_usdjpy_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); sample_runtime(runtime,["USDJPYc"],overwrite=True)
            quality=runtime/"quality"/"QuantGod_MT5FastLaneQuality.json"
            payload={"quality":"FAST","symbols":{"EURUSDc":{"symbol":"EURUSDc","quality":"FAST"}}}
            quality.write_text(json.dumps(payload), encoding="utf-8")
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertEqual(decision["state"],"BLOCKED")
            self.assertFalse(decision["confirmations"]["快通道质量存在"])
            self.assertIn("缺少 MT5 快通道质量证据", "；".join(decision["reasons"]))
    def test_missing_runtime_evidence_blocks_trigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp)
            rows=[
                {"symbol":"USDJPYc","direction":"LONG","horizonMinutes":"15","pips":"4.2","scoreR":"0.42"},
                {"symbol":"USDJPYc","direction":"LONG","horizonMinutes":"15","pips":"2.7","scoreR":"0.27"},
                {"symbol":"USDJPYc","direction":"LONG","horizonMinutes":"15","pips":"1.3","scoreR":"0.13"},
            ]
            ledger=runtime/"ShadowCandidateOutcomeLedger.csv"; runtime.mkdir(parents=True, exist_ok=True)
            with ledger.open("w", encoding="utf-8", newline="") as fh:
                import csv
                writer=csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                writer.writeheader(); writer.writerows(rows)
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertEqual(decision["state"],"BLOCKED")
            self.assertFalse(decision["confirmations"]["运行快照存在"])
            self.assertFalse(decision["confirmations"]["快通道质量存在"])
            self.assertFalse(decision["confirmations"]["自适应入场闸门存在"])
            self.assertIn("缺少运行快照", "；".join(decision["reasons"]))
    def test_missing_adaptive_gate_blocks_trigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); sample_runtime(runtime,["USDJPYc"],overwrite=True)
            (runtime/"adaptive"/"QuantGod_DynamicEntryGate.json").unlink()
            plan=build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]); decision=plan["decisions"][0]
            self.assertEqual(decision["state"],"BLOCKED")
            self.assertFalse(decision["confirmations"]["自适应入场闸门存在"])
            self.assertIn("缺少自适应入场闸门证据", "；".join(decision["reasons"]))
    def test_chinese_telegram_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp); sample_runtime(runtime,["USDJPYc"],overwrite=True)
            text=build_telegram_text(build_trigger_plan(runtime,["USDJPYc"],directions=["LONG"]), symbol="USDJPYc")
            self.assertIn("入场触发实验室", text)
            self.assertIn("不会下单", text)
            self.assertNotIn("OrderSend", text)
if __name__ == "__main__": unittest.main()
