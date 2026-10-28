import hashlib, json

base = '/workspace/vast-coding-vm'
amend = f'{base}/docs/PLAN-v2-AMENDMENTS.md'
contract = f'{base}/docs/CONTRACT.md'
ledger = f'{base}/docs/REVIEW-LEDGER.md'

def apply(path, old, new):
    t = open(path).read()
    n = t.count(old)
    assert n == 1, (path, repr(old[:60]), n)
    open(path, 'w').write(t.replace(old, new))

# --- PLAN-v2-AMENDMENTS.md: L3 (A1+A2) and L2 wording (A3) ---
apply(amend,
"- **L3 create reconciliation.** Before create: `find_by_label`; if a live\n"
"  instance already carries the target label, report it (id, label, dph) and\n"
"  exit 1 with a hint to destroy it or pick a new label. After a create-call\n"
"  transport error or 5xx: re-query by label; if found, treat as created and\n"
"  continue to wait. Still NEVER auto-retry a create.",
"- **L3 create reconciliation.** Before create: `find_by_label`; if the\n"
"  lookup itself errors, that is fatal — exit 1 before any create call (a\n"
"  failed guard must never fall through to create). If a live instance\n"
"  already carries the target label, report it (id, label, dph) and exit 1\n"
"  with a hint to destroy it or pick a new label. After a create-call\n"
"  transport error or 5xx: re-query by label; if found, treat as created and\n"
"  continue to wait; if NOT found, the create outcome is UNKNOWN, not\n"
"  \"failed\" — report the offer id + label, tell the user to check the\n"
"  Vast.ai console or `vastvm status` before retrying, and exit 1. Never\n"
"  report a clean failure after an ambiguous create. Still NEVER auto-retry\n"
"  a create.")

apply(amend,
"  never retried. Final failure prints instance id + destroy hint and exits 4\n"
"  (the instance may still be billing).",
"  never retried. Final failure prints instance id + the exact\n"
"  `vastvm destroy <id> --yes` command (runs without a tty) and exits 4\n"
"  (the instance may still be billing).")

# --- CONTRACT.md: §1 (B1-2, B1-7), §3 (B2-3, B2-10), §4 (B2-4) ---
apply(contract,
"- default timeout 30.0 s, overridable per request.",
"- default timeout 30.0 s, overridable per request; `timeout` must be > 0\n"
"  (non-positive -> `ValueError`); urllib connect+read semantics.\n"
"- `body` is always `bytes` (empty response body -> `b\"\"`, never `None`);\n"
"  `headers` is a plain `dict` (not case-insensitive; consumers must not\n"
"  rely on header lookups); `url` is the final URL after redirects.")

apply(contract,
"`_request(method, path, *, body=None, auth=True) -> Any`:",
"Request URL = `base_url + path` verbatim (every path below begins with\n"
"`/`; the default `base_url` has no trailing slash).\n"
"`_request(method, path, *, body=None, auth=True) -> Any`:")

apply(contract,
"- 2xx -> `json.loads(body)` (empty body -> `None`). Never returns a non-2xx.",
"- 2xx -> `json.loads(body)` (empty body -> `None`); a 2xx body that is not\n"
"  valid JSON raises `VastApiError(status, \"invalid JSON in response\")`.\n"
"  Never returns a non-2xx.")

apply(contract,
"`VMInfo` is the only type passed between lifecycle, sshcmd, provision, cli.",
"`VMInfo.from_api(d)` exact defaults: any missing or `null` optional field\n"
"-> `None`; `dph` = `Decimal(str(cu))` from key `\"cu\"` (`None` when `cu` is\n"
"absent, `null`, or unparseable); `ssh_port` coerced via `int()` when\n"
"possible, else `None`; `id` is required — a dict without a usable `id`\n"
"raises `VastvmError(\"instance response without id\")`.\n"
"\n"
"`VMInfo` is the only type passed between lifecycle, sshcmd, provision, cli.")

# --- REVIEW-LEDGER.md: round-2 section ---
section = """
## Round 2 (post-revision re-review, 2026-10-21)

DeepSeek re-reviewed 3 slices (A money safety; B1 transport/errors; B2
api/models/ssh/cli) against the revised docs. Verdicts: REJECT on all
three, 22 findings. Disposition split: 15 findings R (rejected — already
specified verbatim in CONTRACT sect.1-7; the condensed slice summaries
omitted the frozen transport signature, HttpResponse types, error
hierarchy, connection-error mapping, endpoint paths, ssh_argv argv,
key-resolution env var, exit-code table and empty-body rule, all present
on disk), 7 findings A (genuine micro-gaps, patched same day):

- A1 post-create find_by_label not-found outcome unspecified -> A -> L3
  rewritten: not-found = UNKNOWN outcome; report offer id + label; advise
  console/status check; exit 1; never a clean failure after an ambiguous
  create.
- A2 pre-create find_by_label error path unspecified -> A -> L3: lookup
  error is fatal, exit 1 BEFORE any create call.
- A3 destroy-hint tty safety -> R (CONTRACT sect.7 already prints the
  exact `vastvm destroy <id> --yes`); L2 wording aligned to that string.
- A4 no implementation code supplied -> R (by design: this gate reviews
  the plan; code review follows implementation).
- B1-2 HttpResponse body/None ambiguity -> A -> sect.1: body always
  bytes, empty -> b""; headers plain dict; url final after redirects.
- B1-7 timeout semantics -> A -> sect.1: timeout > 0 else ValueError.
- B2-3 2xx invalid JSON -> A -> sect.3: raises VastApiError(status,
  "invalid JSON in response").
- B2-4 VMInfo defaults -> A -> sect.4: exact None/Decimal/int coercion
  table; missing id raises VastvmError.
- B2-10 base_url joining -> A -> sect.3: base_url + path verbatim.
- B1-1/3/4/5/6/8 and B2-1/2/5/6/7/8/9 -> R: fully specified on disk.

Qwen round-2 re-review: dispatched in parallel (child reviews the same
revision); verdict recorded when it returns.
"""
t = open(ledger).read()
open(ledger, 'w').write(t.rstrip('\n') + '\n' + section)

# --- verification: anchors present, no corruption tokens, sizes ---
for path in (amend, contract, ledger):
    t = open(path).read()
    assert not any(b in t for b in ['num_gops', 'TODO', 'FIXME', 'PLACEHOLDER', '???'])
new_anchors = {
  amend: ['outcome is UNKNOWN', 'fatal — exit 1 before any create call',
          'runs without a tty'],
  contract: ['must be > 0', 'b""', 'invalid JSON in response',
             'base_url + path verbatim', 'instance response without id'],
  ledger: ['Round 2 (post-revision re-review', '22 findings', '7 findings A'],
}
for path, anchors in new_anchors.items():
    t = open(path).read()
    miss = [a for a in anchors if a not in t]
    assert not miss, (path, miss)

sizes = {p.split('/')[-1]: len(open(p).read()) for p in (amend, contract, ledger)}

# --- round-3 delta-confirmation payloads (programmatic, verified) ---
DELTA = ("ROUND-3 delta confirmation. Round 2 found 22 issues: 15 were already "
         "specified on disk (slice-summary artifact, disposition R), 7 genuine, "
         "all now patched. The 7 fixes, verbatim from the amended docs: 1) L3 "
         "post-create re-query by label when NOT found: outcome is UNKNOWN not "
         "failed; report offer id plus label; advise Vast.ai console or vastvm "
         "status check before retrying; exit 1; never a clean failure after an "
         "ambiguous create. 2) L3 pre-create find_by_label lookup error is "
         "fatal, exit 1 BEFORE any create call. 3) Contract sect 1: body is "
         "always bytes, empty response body becomes b-quote-emptyquote, never "
         "None; headers plain dict, not case-insensitive; url is final after "
         "redirects. 4) Sect 1: timeout must be greater than 0, non-positive "
         "raises ValueError, urllib connect plus read semantics. 5) Sect 3: "
         "request URL equals base_url plus path verbatim, paths begin with "
         "slash, base_url has no trailing slash. 6) Sect 3: a 2xx body that is "
         "not valid JSON raises VastApiError with message invalid JSON in "
         "response. 7) Sect 4 VMInfo.from_api exact defaults: missing or null "
         "optional field becomes None; dph is Decimal of str of cu, None when "
         "cu absent null or unparseable; ssh_port coerced via int when "
         "possible else None; id required, dict without usable id raises "
         "VastvmError instance response without id. Additionally L2 final "
         "failure now prints the exact destroy command with --yes flag, safe "
         "without a tty. Question: with these 7 fixes applied, are your round-2 "
         "blockers resolved? List any REMAINING blocker in the amended text, "
         "else APPROVE. First line VERDICT: APPROVE or VERDICT: REJECT, then "
         "numbered findings with severity and evidence.")
assert '\n' not in DELTA and '"' not in DELTA and '`' not in DELTA and all(ord(c) < 128 for c in DELTA)
p3 = [{"name": "coding_model_stage",
       "arguments": {"tasks": [{"role": "coding-build-deepseek", "context": DELTA}]}}]
s3 = json.dumps(p3); json.loads(s3)
open(f'{base}/.reviews/payload-round3-delta-bare.json', 'w').write(s3)

print(json.dumps({
  'sizes': sizes,
  'round3_ctx_chars': len(DELTA), 'round3_payload_chars': len(s3),
  'round3_ctx_sha256': hashlib.sha256(DELTA.encode()).hexdigest(),
  'edits_applied': 7, 'ledger_round2': True,
}, indent=1))