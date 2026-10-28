import hashlib, json

base = '/workspace/vast-coding-vm'
amend, ledger = (f'{base}/docs/{n}' for n in ('PLAN-v2-AMENDMENTS.md', 'REVIEW-LEDGER.md'))

def apply(path, old, new):
    t = open(path).read()
    n = t.count(old)
    assert n == 1, (path.split('/')[-1], n, repr(old[:50]))
    open(path, 'w').write(t.replace(old, new))

# Fix D4-3: re-query-by-label call itself failing -> also UNKNOWN, exit 5
apply(amend,
"  `new_contract` — the outcome is ambiguous until reconciled: re-query by\n"
"  label; if found, treat as created and continue to wait; if NOT found,",
"  `new_contract` — the outcome is ambiguous until reconciled: re-query by\n"
"  label. If the re-query itself fails (transport error, timeout, HTTP\n"
"  5xx), the outcome is likewise UNKNOWN: same report and exit 5. If\n"
"  found, treat as created and continue to wait, and report the matched\n"
"  instance id so the user can verify it in the console (with the L5\n"
"  label lock held, this can only be the instance this run created); if\n"
"  NOT found,")

# Fix D4-4: L5 label lock (append as a new amendment)
t = open(amend).read()
assert 'L5 label lock' not in t
t = t.rstrip('\n') + "\n" + """
- **L5 label lock.** `up` takes an exclusive `flock` on
  `~/.config/vastvm/locks/<label>.lock` (created with parents) for the
  whole run — guard, create, wait, provision — and releases it on exit.
  If the lock is already held, exit 1 with a message that another
  `vastvm up` for this label is running. This makes guard→create atomic
  per host, so a reconcile-by-label match can only be the instance this
  run created. Concurrent `up` runs with the same label from different
  hosts are unsupported and documented in `vastvm up --help`.
"""
open(amend, 'w').write(t)

# Ledger round-4 section
section = """
## Round 4 (delta confirmation, 2026-10-21)

DeepSeek delta-confirmed the exit-5 fix (D4, sha aa0bb625...): REJECT,
5 findings. Dispositions:

- D4-1/D4-2 [Blocker] no code diff / test output -> R (gate conflation:
  this is the plan gate; the same reviewer accepted "code review follows
  implementation" when APPROVEing the contracts slice in round 3. The
  requested evidence — UNKNOWN-path exit-5 tests, create-failure-matrix
  tests — is exactly what test_contract.py / test_cli.py produce at the
  implementation gate.)
- D4-3 [High] re-query-by-label call itself failing, outcome undefined ->
  A -> L3: re-query failure is likewise UNKNOWN, same report and exit 5.
- D4-4 [High] stale/same-label false match at reconcile -> A -> new L5
  label lock (host-local flock for the whole up run; guard->create atomic
  per host; reconcile reports the matched instance id for console
  verification; cross-host same-label concurrency documented unsupported).
  Note: destroyed instances leave /instances/, and an abandoned live
  same-label instance is caught by the pre-create guard, so with L5 the
  false-match window requires cross-host concurrency only.
- D4-5 [Medium] changed-files list -> supplied: this round touches only
  docs/PLAN-v2-AMENDMENTS.md and docs/REVIEW-LEDGER.md (previous round
  also docs/CONTRACT.md, exit-5 row). No builder-owned files exist yet.

Round-5 delta dispatched with fixes 3+4, the changed-files list, and the
plan-gate framing. Qwen round-2 re-review still pending.
"""
t = open(ledger).read()
assert t.count('## Round 4') == 0
open(ledger, 'w').write(t.rstrip('\n') + '\n' + section)

# verify
t = open(amend).read()
for a in ['If the re-query itself fails', 'likewise UNKNOWN: same report and exit 5',
          'L5 label lock', 'releases it on exit', 'different\n  hosts are unsupported']:
    assert a in t, a
assert not any(b in t for b in ['num_gops', 'TODO', 'FIXME', 'PLACEHOLDER', '???'])

D5 = ("ROUND-5 delta confirmation money safety. Fix for your round-4 finding 3: L3 now "
      "states that if the re-query-by-label call itself fails (transport error, "
      "timeout, HTTP 5xx) the outcome is likewise UNKNOWN: same report, exit 5. Fix "
      "for finding 4: new L5 label lock. vastvm up takes an exclusive flock on the "
      "config-dir locks path for the label, held for the whole run (guard, create, "
      "wait, provision), released on exit; lock already held means exit 1 with a "
      "message that another vastvm up for this label is running. This makes "
      "guard-then-create atomic per host, so a reconcile-by-label match can only be "
      "the instance this run created; reconcile also reports the matched instance id "
      "for console verification. Destroyed instances leave the instances list, and "
      "an abandoned live same-label instance is caught by the pre-create guard, so "
      "the remaining false-match window is cross-host same-label concurrency only, "
      "documented as unsupported in up help. For finding 5, the complete "
      "changed-files list for rounds 3-4: docs PLAN-v2-AMENDMENTS.md, "
      "REVIEW-LEDGER.md, CONTRACT.md (one exit-table row). No builder-owned files "
      "exist yet. Scope note for findings 1 and 2: this is the plan gate; you "
      "accepted the same framing when approving the contracts slice in round 3 "
      "(code review follows implementation). The evidence you ask for (UNKNOWN-path "
      "exit-5 test output, create-failure-matrix tests) is produced by the "
      "conformance suite at the implementation gate, immediately after this gate "
      "passes. Question: at the PLAN level, are findings 3 and 4 resolved, and is "
      "the plan ready for the two builders to start? First line VERDICT: APPROVE "
      "or VERDICT: REJECT, then numbered findings with severity and evidence.")
assert '\n' not in D5 and '"' not in D5 and '`' not in D5 and all(ord(c) < 128 for c in D5)
payload = [{"name": "coding_model_stage",
            "arguments": {"tasks": [{"role": "coding-build-deepseek", "context": D5}]}}]
s = json.dumps(payload); json.loads(s)
open(f'{base}/.reviews/payload-round5-delta-bare.json', 'w').write(s)
print(json.dumps({'d5_ctx': len(D5), 'd5_payload': len(s),
                  'd5_sha': hashlib.sha256(D5.encode()).hexdigest(),
                  'amend_chars': len(open(amend).read())}))