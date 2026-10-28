import hashlib, json

base = '/workspace/vast-coding-vm'
contract = open(f'{base}/docs/CONTRACT.md').read()
amend = open(f'{base}/docs/PLAN-v2-AMENDMENTS.md').read()
ledger = f'{base}/docs/REVIEW-LEDGER.md'

# ---------- ledger: round-5 section ----------
assert '## Round 5' not in open(ledger).read()
open(ledger, 'a').write("""
## Round 5 (delta confirmation, 2026-10-21)

DeepSeek delta-confirmed the L3/L5 fixes (D5, sha 0009f263...): APPROVE.
Finding 3 (re-query failure UNKNOWN) and finding 4 (label-lock
atomicity; cross-host residual documented unsupported) both resolved.
Findings 1/2 correctly re-framed as implementation-gate evidence,
consistent with the round-3 contracts APPROVE. DEEPSEEK PLAN GATE
PASSED (contracts r3 APPROVE, money-safety r5 APPROVE). Implementation
may begin once the Qwen round-2 re-review verdict lands.
""")

# ---------- mechanical transport transform ----------
def tx(t):
    t = (t.replace('`', '').replace('"', "'").replace('—', '--')
          .replace('→', '->').replace('≤', '<=').replace('≥', '>=')
          .replace('\u2014', '--'))
    out = []
    for raw in t.splitlines():
        s = raw.strip()
        if not s: continue
        ind = (len(raw) - len(raw.lstrip())) // 2
        out.append('.' * ind + s)
    r = ' | '.join(out)
    assert all(ord(c) < 128 for c in r) and '"' not in r and '\n' not in r
    return r

def section(doc, start, end=None):
    i = doc.index(start)
    j = doc.index(end, i) if end else len(doc)
    return doc[i:j]

# contract sections (verbatim, by heading markers)
S0   = section(contract, '## 0. Modules and ownership', '## 1.')
S1   = section(contract, '## 1. Transport', '## 2.')
S2   = section(contract, '## 2. Errors', '## 3.')
S3   = section(contract, '## 3. API client', '## 4.')
S4   = section(contract, '## 4. Shared model', '## 5.')
S5   = section(contract, '## 5. Domain signatures', '## 6.')
S8   = section(contract, '## 8. Money-safety invariants')
S5o  = section(S5, '# offers.py', '# lifecycle.py')
S5l  = section(S5, '# lifecycle.py', '# sshcmd.py')
S5s  = section(S5, '# sshcmd.py', '# cost.py')
S5c  = section(S5, '# cost.py')
# amendment blocks
AL   = section(amend, '## Lifecycle (money safety)', '## CLI / confirmation')
ACV  = section(amend, '## Cost / visibility', '## Provision')

PREAMBLE = ("IMPLEMENTATION Builder A (DeepSeek). Repo vast-coding-vm, stdlib-only "
            "Python >= 3.11 (tomllib allowed), package dir vastvm/, tests pytest, no "
            "network in tests (inject fakes). SPEC VERBATIM from the frozen contract: "
            "newlines shown as ' | ', indentation as dots (one dot per two spaces), "
            "backticks removed, double quotes shown as single quotes. Implement "
            "EXACTLY the spec, no extra features, no TODOs. Money values are Decimal, "
            "never float. Return for EACH file you own: a line 'FILE: <path>' then the "
            "complete source in one fenced code block, then note any spec point you "
            "could not satisfy. ")

slices = {
 'imp-a-errors': (PREAMBLE + "You own vastvm/errors.py and tests/test_errors.py. "
        "Ownership context: " + tx(S0) + " Spec sect 2 Errors: " + tx(S2)),
 'imp-a-models': (PREAMBLE + "You own vastvm/models.py and tests/test_models.py. "
        "Spec sect 4 Shared model: " + tx(S4)),
 'imp-a-transport': (PREAMBLE + "You own vastvm/transport.py and tests/test_transport.py. "
        "Spec sect 1 Transport: " + tx(S1)),
 'imp-a-api': (PREAMBLE + "You own vastvm/api.py and tests/test_api.py. "
        "Spec sect 3 API client: " + tx(S3) + " Spec sect 8 money-safety invariants: " + tx(S8)),
 'imp-a-offers-cost': (PREAMBLE + "You own vastvm/offers.py, vastvm/cost.py, "
        "tests/test_offers.py, tests/test_cost.py. Spec sect 5 offers.py: " + tx(S5o) +
        " Spec sect 5 cost.py: " + tx(S5c) + " Amendment cost/visibility: " + tx(ACV)),
 'imp-a-lifecycle': (PREAMBLE + "You own vastvm/lifecycle.py and tests/test_lifecycle.py. "
        "Spec sect 5 lifecycle.py: " + tx(S5l) + " Amendments lifecycle money safety: " + tx(AL) +
        " Spec sect 8 money-safety invariants: " + tx(S8)),
 'imp-a-sshcmd': (PREAMBLE + "You own vastvm/sshcmd.py and tests/test_sshcmd.py. "
        "Spec sect 5 sshcmd.py: " + tx(S5s)),
}

out = {}
for tag, text in slices.items():
    open(f'{base}/.reviews/{tag}.txt', 'w').write(text)
    payload = [{"name": "coding_model_stage",
                "arguments": {"tasks": [{"role": "coding-build-deepseek", "context": text}]}}]
    s = json.dumps(payload); json.loads(s)
    open(f'{base}/.reviews/payload-{tag}-bare.json', 'w').write(s)
    out[tag] = dict(ctx=len(text), payload=len(s),
                    sha=hashlib.sha256(text.encode()).hexdigest()[:12])

# ---------- builder-B delegate goal (staged for next turn) ----------
goal = open(f'{base}/.reviews/builder-b-goal.md', 'w')
goal.write("""IMPLEMENTATION Builder B (qwen3-coder). Work ONLY in /workspace/vast-coding-vm.

READ FIRST (authority order): docs/CONTRACT.md (sect 0 ownership, 6 config, 7 CLI, 8 money-safety invariants; sect 1-5 define Builder A modules you import but MUST NOT create or edit), docs/PLAN-v2-AMENDMENTS.md (C1-C3, U1, S1, P1-P3, V1), docs/PLAN.md (sect 3 specs for config.py / provision.py / cli.py / provision.sh, sect 6 test plan).

YOU OWN EXACTLY (create only these): vastvm/config.py, vastvm/provision.py, vastvm/cli.py, vastvm/__init__.py, vastvm/__main__.py, provision/provision.sh, pyproject.toml, tests/test_config.py, tests/test_provision.py, tests/test_cli.py. NEVER touch any Builder A file (errors/transport/api/models/offers/lifecycle/sshcmd/cost) or tests/test_contract.py (coordinator-owned).

KEY RULES: stdlib-only Python >= 3.11; Money = Decimal never float; exit codes 0/1/2/3/4/5 per contract sect 7; vastvm ssh interactive passthrough uses batch=False, all scripted ssh batch=True; --force never implies --yes, non-tty without --yes exits 3; U1 shows dph + monthly before confirm; provision.sh target <= 380 lines MUST pass bash -n; P1-P3 and V1 per amendments; CLI orchestrates Builder A modules strictly via the frozen signatures in contract sect 1-5.

TESTING STANDALONE: Builder A files may not exist yet. Your tests must inject contract-faithful fakes into sys.modules for vastvm.errors/transport/api/models/offers/lifecycle/sshcmd/cost BEFORE importing vastvm.cli (pytest fixture at module top), so your suite runs green standalone. The coordinator reruns everything after integration.

VERIFY before finishing: python3 -m pytest tests/test_config.py tests/test_provision.py tests/test_cli.py green; bash -n provision/provision.sh clean; python3 -m vastvm --help works with fakes injected. Report files written, test results, and any contract point you could not satisfy.""")
goal.close()

print(json.dumps({'slices': out,
  'ledger_round5': True,
  'builder_b_goal_staged': True}, indent=1))