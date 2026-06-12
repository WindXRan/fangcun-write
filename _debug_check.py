import json
import sys

d = json.loads(open(sys.argv[1], encoding='utf-8').read())
results = d.get('results', {})
errors = {k: v for k, v in results.items() if v.get('status') == 'error'}
print(f'Total errors: {len(errors)}')
for k in sorted(errors, key=lambda x: int(x))[:10]:
    e = errors[k]
    print(f'  ch{k}: {str(e.get("error", "no error msg"))[:120]}')
missing = {k: v for k, v in results.items() if v.get('status') == 'missing'}
print(f'Missing: {len(missing)}')
