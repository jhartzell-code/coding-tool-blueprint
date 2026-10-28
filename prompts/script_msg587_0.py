import json

base = '/workspace/vast-coding-vm'
for name in ('CONTRACT.md', 'PLAN-v2-AMENDMENTS.md', 'PLAN.md'):
    t = open(f'{base}/docs/{name}').read()
    lines = t.splitlines()
    heads = [(i+1, l) for i, l in enumerate(lines) if l.startswith('#')]
    print(f'== {name} ({len(t)} chars, {len(lines)} lines) ==')
    for n, h in heads:
        print(f'  L{n}: {h[:90]}')