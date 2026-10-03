#!/usr/bin/env python3
"""Extract enrich/verify/discover agent results from workflow journal.jsonl files.
Usage: parse_journal.py <journal1> [<journal2> ...]
Writes enriched.json, verifications.json, discovered.json next to this script.
"""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
enriched, verifs, discovered, notes = [], [], [], []
key2label = {}
stats = {}
for path in sys.argv[1:]:
    region = 'Broward' if 'ab075d6f' in path else 'Palm Beach + Miami-Dade'
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            t = rec.get('type')
            stats[t] = stats.get(t, 0) + 1
            if t == 'started':
                key2label[rec.get('key')] = rec.get('label', '')
                continue
            if t not in ('completed', 'result', 'finished', 'done'):
                continue
            label = rec.get('label') or key2label.get(rec.get('key'), '')
            res = rec.get('result')
            if res is None:
                res = rec.get('value')
            if isinstance(res, str):
                try:
                    res = json.loads(res)
                except Exception:
                    continue
            if not isinstance(res, dict):
                continue
            if label.startswith('enrich'):
                for c in res.get('companies', []):
                    c['region'] = region
                    enriched.append(c)
            elif label.startswith('verify'):
                verifs.extend(res.get('companies', []))
            elif label.startswith('discover'):
                for c in res.get('candidates', []):
                    c['region'] = region; c['angle'] = label
                    discovered.append(c)
                notes.append({'angle': label, 'notes': res.get('notes', '')})
for name, obj in (('enriched.json', enriched), ('verifications.json', verifs), ('discovered.json', discovered), ('discovery_notes.json', notes)):
    with open(os.path.join(HERE, name), 'w') as f:
        json.dump(obj, f, indent=1)
print(json.dumps({'record_types': stats, 'enriched': len(enriched), 'verifications': len(verifs), 'discovered': len(discovered)}))
