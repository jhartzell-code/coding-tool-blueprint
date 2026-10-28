import json

base = '/workspace/vast-coding-vm'
amend, contract, ledger = (f'{base}/docs/{n}' for n in
    ('PLAN-v2-AMENDMENTS.md', 'CONTRACT.md', 'REVIEW-LEDGER.md'))

# 1) L3 patch (round-3 D1-1 + D1-2): any create-call failure is ambiguous; UNKNOWN exits 5
old_l3 = """- **L3 create reconciliation.** Before create: `find_by_label`; if the
  lookup itself errors, that is fatal — exit 1 before any create call (a
  failed guard must never fall through to create). If a live instance
  already carries the target label, report it (id, label, dph) and exit 1
  with a hint to destroy it or pick a new label. After a create-call
  transport error or 5xx: re-query by label; if found, treat as created and
  continue to wait; if NOT found, the create outcome is UNKNOWN, not
  "failed" — report the offer id + label, tell the user to check the
  Vast.ai console or `vastvm status` before retrying, and exit 1. Never
  report a clean failure after an ambiguous create. Still NEVER auto-retry
  a create."""
new_l3 = """- **L3 create reconciliation.** Before create: `find_by_label`; if the
  lookup itself errors, that is fatal — exit 1 before any create call (a
  failed guard must never fall through to create). If a live instance
  already carries the target label, report it (id, label, dph) and exit 1
  with a hint to destroy it or pick a new label. After ANY create-call
  failure — transport error, timeout, HTTP 5xx, or a 2xx response missing
  `new_contract` — the outcome is ambiguous until reconciled: re-query by
  label; if found, treat as created and continue to wait; if NOT found,
  the create outcome is UNKNOWN, not "failed" — report the offer id +
  label, tell the user to check the Vast.ai console or `vastvm status`
  before retrying, and exit 5 (distinct from exit 1: exit-1 failures are
  safe for a wrapper to retry once the guard re-runs, while an UNKNOWN
  outcome must never be auto-retried). Never report a clean failure after
  an ambiguous create. Still NEVER auto-retry a create."""
t = open(amend).read()
assert t.count(old_l3) == 1, f'L3 anchor count = {t.count(old_l3)}'
open(amend, 'w').write(t.replace(old_l3, new_l3))

# 2) ledger round-3 section
section = """
## Round 3 (delta confirmation, 2026-10-21)

DeepSeek re-reviewed the 7 round-2 patches as two delta slices.
Contracts slice (D2, sha 65a74c93...): APPROVE — all 5 contract fixes
confirmed against the on-disk text, 13 R-dispositions accepted.
Contracts gate PASSED. Money-safety slice (D1, sha eec4dfa8...): REJECT,
2 High findings, both accepted as genuine:

- D1-1 create error/timeout path not explicitly mapped to UNKNOWN -> A ->
  L3 rewritten: ANY create-call failure (transport error, timeout, HTTP
  5xx, or 2xx missing new_contract) is ambiguous until reconciled; same
  re-query-by-label, same UNKNOWN handling, same console-check advice.
- D1-2 exit-1 collision: UNKNOWN (unsafe to retry) shared exit 1 with
  clean failures (safe to retry) -> A -> new exit code 5 exclusively for
  the UNKNOWN ambiguous-create outcome; contract exit table updated so
  wrapper scripts can distinguish retry-safe from retry-unsafe failures.

Round-4 delta confirmation dispatched on these two fixes. Qwen round-2
re-review still pending (background child).
"""
t = open(ledger).read()
assert t.count('## Round 3') == 0
open(ledger, 'w').write(t.rstrip('\n') + '\n' + section)
print('round-3 msg560 patches applied')
