import json, re, sys
d = json.load(open(sys.argv[1])); errs = []
def res(ref):
    n = d
    for p in ref[2:].split('/'): n = n[p]
    return n
def walk(n, path):
    if isinstance(n, dict):
        if '$ref' in n:
            try: res(n['$ref'])
            except Exception: errs.append(f'dangling {n["$ref"]} at {path}')
        for k, v in n.items(): walk(v, path + '/' + k)
    elif isinstance(n, list):
        for i, v in enumerate(n): walk(v, f'{path}/{i}')
walk(d, '')
T = {'object': dict, 'array': list, 'string': str, 'boolean': bool}
def allprops(s):
    if '$ref' in s: s = res(s['$ref'])
    ps = set(s.get('properties', {}))
    for a in s.get('allOf', []): ps |= allprops(a)
    return ps
def val(s, v, p, out, strict=True):
    if '$ref' in s: return val(res(s['$ref']), v, p, out, strict)
    t = s.get('type')
    if t in T and not isinstance(v, T[t]): out.append(f'{p}: not {t}'); return
    if t == 'integer' and (isinstance(v, bool) or not isinstance(v, int)): out.append(f'{p}: not integer'); return
    if t == 'number' and (isinstance(v, bool) or not isinstance(v, (int, float))): out.append(f'{p}: not number'); return
    if 'enum' in s and v not in s['enum']: out.append(f'{p}: {v!r} not in enum')
    if 'const' in s and v != s['const']: out.append(f'{p}: not const')
    if 'pattern' in s and isinstance(v, str) and not re.search(s['pattern'], v): out.append(f'{p}: pattern')
    for k, f in (('minimum', lambda a, b: a >= b), ('maximum', lambda a, b: a <= b), ('exclusiveMinimum', lambda a, b: a > b)):
        if k in s and isinstance(v, (int, float)) and not f(v, s[k]): out.append(f'{p}: {k}')
    if 'minItems' in s and isinstance(v, list) and len(v) < s['minItems']: out.append(f'{p}: minItems')
    for a in s.get('allOf', []): val(a, v, p, out, False)
    if 'allOf' in s and isinstance(v, dict) and strict and not any('oneOf' in (res(m['$ref']) if '$ref' in m else m) for m in s['allOf']):
        for k in v:
            if k not in allprops(s): out.append(f'{p}: unknown property {k} (typo check)')
    for key in ('anyOf', 'oneOf'):
        if key in s:
            ok = 0
            for a in s[key]:
                o = []; val(a, v, p, o); ok += not o
            if ok == 0 or (key == 'oneOf' and ok != 1): out.append(f'{p}: {key} matched {ok}')
    if isinstance(v, dict):
        for r in s.get('required', []):
            if r not in v: out.append(f'{p}: missing {r}')
        props = s.get('properties', {})
        for k, x in v.items():
            if k in props: val(props[k], x, f'{p}/{k}', out)
            elif strict and props and 'allOf' not in s and 'oneOf' not in s: out.append(f'{p}: unknown property {k} (typo check)')
    if isinstance(v, list) and 'items' in s:
        for i, x in enumerate(v): val(s['items'], x, f'{p}/{i}', out)
S = '#/components/schemas/'
M = {'Capabilities': 'Capabilities', 'QueryCabinetsAndDensity': 'QueryRequest', 'QueryPowerOnly': 'QueryRequest', 'AnswerGradeOnly': 'CapacityAnswer', 'AnswerBanded': 'CapacityAnswer', 'SignalRequest': 'SignalRequest', 'SubscriptionWebhook': 'SubscriptionRequest', 'EventAnswerUpdated': 'Event', 'ProblemInconsistentDemand': 'Problem'}
for ex, sc in M.items():
    o = []; val({'$ref': S + sc}, d['components']['examples'][ex]['value'], ex, o); errs += o
assert set(M) <= set(d["components"]["examples"])
# negative checks
neg = [('LocationRef', {'level': 'AREA', 'center': {'latitude': 50.1, 'longitude': 8.7}}), ('Timing', {'status': 'PLANNED', 'availableForService': 'SOON'}), ('DensityRange', {'unit': 'KVA'}), ('Demand', {'cabinets': {'count': 4}}), ('SubscriptionRequest', {'delivery': {'type': 'PULL'}}), ('DesiredFeature', {'feature': 'LIQUID_COOLING'}), ('Timeframe', {'neededForSale': '06/2027'}), ('CapacityRequirement', {'locations': [{'level': 'METRO', 'code': 'DEFRA'}], 'demand': {'power': {'value': 1, 'unit': 'MW'}}, 'timeframe': {'neededForService': '2027-Q5'}})]
for sc, v in neg:
    o = []; val({'$ref': S + sc}, v, sc, o)
    if not o: errs.append(f'negative case accepted: {sc} {v}')
def answers(n):
    if isinstance(n, dict):
        if 'results' in n and 'answerId' in n: yield n
        for v in n.values(): yield from answers(v)
    elif isinstance(n, list):
        for v in n: yield from answers(v)
for a in answers(d['components']['examples']):
    for r in a['results']:
        if r['grade'] in ('AVAILABLE', 'POSSIBLE'):
            for f in r['supportedFeatures']:
                if f.get('required') and f['support'] not in ('AVAILABLE', 'POSSIBLE'):
                    errs.append('required-feature rule broken in ' + a['answerId'])
used = set(re.findall(r'#/components/schemas/(\w+)', json.dumps(d)))
unused = set(d['components']['schemas']) - used
ops = [o.get('operationId') for p in list(d['paths'].values()) + list(d['webhooks'].values()) for m, o in p.items() if m in ('get', 'post', 'put', 'delete')]
print('operations', len(ops), 'unique', len(set(ops)), 'schemas', len(d['components']['schemas']), 'unused', unused)
print('\n'.join(errs) or 'OK: refs resolve, examples validate, negative cases rejected')

# ---- exchanges: every step is validated against the operation it names
ops_by_id = {}
for group in ('paths', 'webhooks'):
    for path, item in d[group].items():
        for m, o in item.items():
            if m in ('get', 'post', 'put', 'delete'): ops_by_id[o['operationId']] = (m.upper(), path, o)
def deref(n):
    return res(n['$ref']) if '$ref' in n else n
xerrs, used_ex, steps = [], set(), 0
for sc in d['x-exchanges']:
    for st in sc['steps']:
        steps += 1
        tag = sc['id'] + ' / ' + st['title']
        if st['operationId'] not in ops_by_id: xerrs.append(tag + ': unknown operation'); continue
        m, path, o = ops_by_id[st['operationId']]
        rq, rs = st['request'], st['response']
        if rq['method'] != m: xerrs.append(tag + ': method')
        if not rq['path'].startswith('http') and not re.fullmatch(re.sub(r'\{[^}]+\}', '[^/?]+', path) + r'(\?.*)?', rq['path']): xerrs.append(tag + ': path ' + rq['path'])
        if 'example' in rq:
            used_ex.add(rq['example'])
            body = deref(o['requestBody'])['content']
            schema = list(body.values())[0]['schema']
            out = []; val(schema, d['components']['examples'][rq['example']]['value'], rq['example'], out); xerrs += [tag + ': ' + e for e in out]
        code = str(rs['status'])
        resp = o['responses'].get(code) or o['responses'].get('default')
        if code not in o['responses'] and code not in ('200',): xerrs.append(tag + ': status %s not declared' % code)
        if 'example' in rs:
            used_ex.add(rs['example'])
            content = deref(resp)['content']
            schema = (content.get('application/json') or content.get('application/problem+json'))['schema']
            v = d['components']['examples'][rs['example']]['value']
            out = []; val(schema, v, rs['example'], out); xerrs += [tag + ': ' + e for e in out]
            if 'status' in v and 'code' in v and v['status'] != rs['status']: xerrs.append(tag + ': problem status differs')
        if 'rawBody' in rq and json.loads(rq['rawBody']) != d['components']['examples'][rq['example']]['value']: xerrs.append(tag + ': rawBody differs from example')
        if 'signature' in rq:
            import hmac, hashlib
            s = rq['signature']; h = hmac.new(s['signingSecret'].encode(), ('%d.%s' % (s['timestamp'], rq['rawBody'])).encode(), hashlib.sha256).hexdigest()
            if h != s['value'] or rq['headers']['OpenCapacity-Signature'] != 't=%d,v1=%s' % (s['timestamp'], h): xerrs.append(tag + ': signature')
        for key in ('text',):
            if key in rs:
                for line in rs[key].split('\n'):
                    if line.startswith('data: '):
                        out = []; val({'$ref': S + 'Event'}, json.loads(line[6:]), 'sse', out); xerrs += [tag + ': ' + e for e in out]
orphans = set(d['components']['examples']) - used_ex
print('examples', len(d['components']['examples']), 'exchange steps', steps, 'examples not used in an exchange', sorted(orphans))
print('\n'.join(xerrs) or 'OK: every exchange step matches its operation and validates')
