import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const files = [
  'tools/execution_feedback_producer/schema.py',
  'tools/execution_feedback_producer/io_utils.py',
  'tools/execution_feedback_producer/producer.py',
  'tools/execution_feedback_producer/telegram_text.py',
  'tools/run_execution_feedback_producer.py',
  'tests/test_execution_feedback_producer.py',
];

for (const file of files) {
  test(`${file} is readable source`, () => {
    const text = readFileSync(file, 'utf8');
    const lines = text.split(/\r?\n/);
    assert.ok(lines.length >= 10, `${file} should be multi-line source`);
    const longLine = lines.find((line) => line.length > 220);
    assert.equal(longLine, undefined, `${file} has an overly long line`);
  });
}

test('execution feedback producer does not introduce trading execution', () => {
  const text = files.map((file) => readFileSync(file, 'utf8')).join('\n');
  for (const token of ['OrderSend', 'PositionClose', 'TRADE_ACTION_DEAL', 'livePresetMutationAllowed = True']) {
    assert.equal(text.includes(token), false, `forbidden token found: ${token}`);
  }
});
