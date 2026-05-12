"""Regression tests for the GA Factory compatibility CLI alias."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tools.run_ga_factory import main as ga_factory_main
from tools.strategy_ga_factory.factory_runner import read_factory_state


class GAFactoryAliasTests(unittest.TestCase):
    def test_alias_runner_builds_same_factory_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                sample_code = ga_factory_main(["--runtime-dir", str(runtime_dir), "sample", "--overwrite"])
            self.assertEqual(sample_code, 0)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                build_code = ga_factory_main(["--runtime-dir", str(runtime_dir), "build", "--write"])
            self.assertEqual(build_code, 0)

            state = read_factory_state(runtime_dir)
            self.assertEqual(state["schema"], "quantgod.strategy_ga_factory.state.v1")
            self.assertGreater(state["candidateCount"], 0)
            self.assertFalse(state["safety"]["orderSendAllowed"])


if __name__ == "__main__":
    unittest.main()
