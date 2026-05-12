import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';

const files = [
  'tools/run_production_evidence_validation.py',
  'tools/production_evidence_validation/schema.py',
  'tools/production_evidence_validation/io_utils.py',
  'tools/production_evidence_validation/history_audit.py',
  'tools/production_evidence_validation/parity_audit.py',
  'tools/production_evidence_validation/execution_feedback_audit.py',
  'tools/production_evidence_validation/ga_audit.py',
  'tools/production_evidence_validation/report.py',
  'tools/production_evidence_validation/telegram_text.py',
  'Dashboard/production_evidence_validation_api_routes.js',
];

test('P4-6 sources are readable and not compressed into one line', () => {
  for (const file of files) {
    const text = readFileSync(file, 'utf8');
    const lines = text.split(/\r?\n/);
    assert.ok(lines.length >= 8, `${file} should be multi-line`);
    const longest = Math.max(...lines.map((line) => line.length));
    assert.ok(longest <= 220, `${file} has too long line: ${longest}`);
    assert.equal(/import .* def /.test(text), false, `${file} contains compressed Python`);
    assert.equal(/;\s*def\s+/.test(text), false, `${file} contains semicolon-def compression`);
  }
});

test('P4-6 guard blocks trading verbs and direct wallet semantics', () => {
  const joined = files.map((file) => readFileSync(file, 'utf8')).join('\n');
  for (const forbidden of ['OrderSend(', 'CTrade', 'TRADE_ACTION_DEAL', 'PositionClose(', 'livePresetMutationAllowed: true', 'polymarketRealMoneyAllowed: true']) {
    assert.equal(joined.includes(forbidden), false, `forbidden token ${forbidden}`);
  }
});
