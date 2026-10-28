import hashlib, json

base = '/workspace/vast-coding-vm'
contract = f'{base}/docs/CONTRACT.md'

old = """- Exit codes: 0 ok; 1 `VastApiError` / `TransportError` / `ConfigError`
  (message to stderr); 2 argparse usage; 3 confirmation refused; 4 bad
  instance state, wait-timeout, or ssh unreachable after retries — whenever
  a live instance exists the message includes the instance id and the exact
  `vastvm destroy <id> --yes` command."""
new = """- Exit codes: 0 ok; 1 `VastApiError` / `TransportError` / `ConfigError`
  (message to stderr); 2 argparse usage; 3 confirmation refused; 4 bad
  instance state, wait-timeout, or ssh unreachable after retries — whenever
  a live instance exists the message includes the instance id and the exact
  `vastvm destroy <id> --yes` command; 5 ambiguous create outcome (UNKNOWN
  after a create-call failure and failed label reconcile — never
  auto-retryable; check the Vast.ai console or `vastvm status` first)."""
t = open(contract).read()
assert t.count(old) == 1, t.count(old)
open(contract, 'w').write(t.replace(old, new))
print('round-3 msg562 exit-5 row applied')
