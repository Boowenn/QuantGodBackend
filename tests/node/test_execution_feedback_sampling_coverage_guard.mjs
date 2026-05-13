import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const FILES = [
  'tools/production_evidence_validation/execution_feedback_audit.py',
  'tools/production_evidence_validation/report.py',
  'tests/test_execution_feedback_sampling_coverage.py',
];

for (const file of FILES) {
  test(`${file} is readable source`, () => {
    const text = readFileSync(file, 'utf8');
    const lines = text.split(/\r?\n/);
    assert.ok(lines.length >= 20, `${file} should be multi-line source`);
    const longLine = lines.find((line) => line.length > 220);
    assert.equal(longLine, undefined, `${file} has an overly long line`);
  });
}

test('execution feedback coverage exposes production sampling fields', () => {
  const text = readFileSync('tools/production_evidence_validation/execution_feedback_audit.py', 'utf8');
  for (const marker of [
    'coverageGrade',
    'evidenceUsability',
    'coreCoverage',
    'strategyCoverage',
    'numericSummary',
    'recommendationsZh',
  ]) {
    assert.ok(text.includes(marker), `missing coverage marker ${marker}`);
  }
});

test('execution feedback coverage does not introduce trading execution', () => {
  const text = FILES.map((file) => readFileSync(file, 'utf8')).join('\n');
  const forbidden = [
    'OrderSend',
    'PositionClose',
    'TRADE_ACTION_DEAL',
    'livePresetMutationAllowed = True',
    'telegramCommandExecutionAllowed = True',
  ];
  for (const token of forbidden) {
    assert.equal(text.includes(token), false, `Forbidden token found: ${token}`);
  }
});
