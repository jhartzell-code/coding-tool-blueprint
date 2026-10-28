import hashlib, json

base = '/workspace/vast-coding-vm'
amend, contract, ledger = (f'{base}/docs/{n}' for n in
    ('PLAN-v2-AMENDMENTS.md', 'CONTRACT.md', 'REVIEW-LEDGER.md'))

# verification (backtick-aware anchors), read-only
anchors = {
  amend: ['outcome is UNKNOWN', 'exit 1 before any create call'.replace('exit 1', 'fatal — exit 1'),
          'runs without a tty', '`vastvm destroy <id> --yes`'],
  contract: ['must be > 0', 'b""', 'invalid JSON in response',
             '`base_url + path` verbatim', 'instance response without id',
             'final URL after redirects'],
  ledger: ['Round 2 (post-revision re-review', '22 findings', '7 findings A'],
}
report = {}
for path, lst in anchors.items():
    t = open(path).read()
    miss = [a for a in lst if a not in t]
    assert not miss, (path.split('/')[-1], miss)
    assert not any(b in t for b in ['num_gops', 'TODO', 'FIXME', 'PLACEHOLDER', '???'])
    report[path.split('/')[-1]] = len(t)
t = open(ledger).read()
assert t.count('Round 2 (post-revision re-review') == 1, 'ledger section duplicated!'
assert t.count('## Round 1') + t.count('## Round') >= 2

# two compact round-3 delta payloads (proven transport envelope ~<1.4KB each)
D1 = ("ROUND-3 delta confirmation slice 1 money safety. Your round-2 A-slice blockers are now "
      "patched: 1) L3 post-create re-query by label when NOT found: outcome is UNKNOWN not "
      "failed; report offer id plus label; advise Vast.ai console or vastvm status check before "
      "retrying; exit 1; never a clean failure after an ambiguous create. 2) L3 pre-create "
      "find_by_label lookup error is fatal, exit 1 BEFORE any create call; a failed guard never "
      "falls through to create. 3) L2 final ssh failure prints the exact destroy command with "
      "--yes flag, safe without a tty, and exits 4. Round-2 R-dispositions you should accept: "
      "destroy-hint --yes was already in contract sect 7 exit table; no-implementation-code is "
      "by design, this gate reviews the plan and code review follows implementation. Question: "
      "are your round-2 money-safety blockers resolved by these amendments? List any REMAINING "
      "blocker in the amended text, else APPROVE. First line VERDICT: APPROVE or VERDICT: "
      "REJECT, then numbered findings with severity and evidence.")

D2 = ("ROUND-3 delta confirmation slice 2 contracts. Your round-2 B-slice blockers are now "
      "patched, verbatim from the amended contract: 1) sect 1 HttpResponse body is always "
      "bytes, empty body becomes empty bytes never None; headers plain dict not "
      "case-insensitive; url is final after redirects. 2) sect 1 timeout must be greater than "
      "0, non-positive raises ValueError, urllib connect plus read semantics, default 30 "
      "overridable per request. 3) sect 3 request URL equals base_url plus path verbatim, every "
      "path begins with slash, default base_url has no trailing slash. 4) sect 3 a 2xx body "
      "that is not valid JSON raises VastApiError with message invalid JSON in response. 5) "
      "sect 4 VMInfo.from_api exact defaults: missing or null optional field becomes None; dph "
      "is Decimal of str of key cu, None when cu absent null or unparseable; ssh_port coerced "
      "via int when possible else None; id required, dict without usable id raises VastvmError "
      "instance response without id. Your other 13 round-2 findings were R-dispositioned as "
      "already specified on disk in contract sect 1-7: transport signature and HttpResponse "
      "types, error hierarchy and connection-error mapping, endpoint paths, ssh_argv argv, "
      "key-resolution env var, exit-code table, empty-body rule. Question: are your round-2 "
      "contract blockers resolved? List any REMAINING blocker, else APPROVE. First line "
      "VERDICT: APPROVE or VERDICT: REJECT, then numbered findings with severity and evidence.")

out = {}
for tag, text in [('d1', D1), ('d2', D2)]:
    assert '\n' not in text and '"' not in text and '`' not in text
    assert all(ord(c) < 128 for c in text)
    open(f'{base}/.reviews/deepseek-round3-slice-{tag}.txt', 'w').write(text)
    payload = [{"name": "coding_model_stage",
                "arguments": {"tasks": [{"role": "coding-build-deepseek", "context": text}]}}]
    s = json.dumps(payload); json.loads(s)
    open(f'{base}/.reviews/payload-round3-{tag}-bare.json', 'w').write(s)
    out[tag] = dict(ctx=len(text), payload=len(s), budget='ok' if len(s) <= 1450 else 'OVER',
                    sha=hashlib.sha256(text.encode()).hexdigest()[:16])

print(json.dumps({'doc_sizes': report, 'round3': out, 'ledger_sections': 1}, indent=1))