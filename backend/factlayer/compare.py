"""Conservative comparison: unknown context is never silently equal context."""
import re
from decimal import Decimal
from difflib import SequenceMatcher

from . import db
from .pdf import normalize

SCALES = {'one': Decimal(1), 'thousand': Decimal(1000), 'lakh': Decimal(100000),
          'million': Decimal(1000000), 'crore': Decimal(10000000), 'billion': Decimal(1000000000)}


def key(value):
    return re.sub(r'[^\w]+', ' ', normalize(value).lower()).strip()


def numeric(value):
    number = Decimal(value['number'].replace(',', '')) * SCALES[value.get('scale', 'one')]
    unit = key(value.get('unit') or '')
    aliases = {'rupees': 'inr', 'indian rupees': 'inr', '₹': 'inr', '%': 'percent',
               'percentage': 'percent', 'people': 'persons'}
    unit = aliases.get(value.get('unit', ''), aliases.get(unit, unit))
    if unit in ('basis points', 'bps'):
        number /= 100
        unit = 'percentage points'
    return number, unit


def compare(a, b, aligned=False):
    if key(a['subject']) != key(b['subject']):
        return None
    if key(a.get('canonical_predicate', a['predicate'])) != key(b.get('canonical_predicate', b['predicate'])) and not aligned:
        return None
    ca, cb = a.get('context', {}), b.get('context', {})
    context_diff = {k: [ca.get(k), cb.get(k)] for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)}
    result = {'context_comparison': context_diff, 'certainty': 'bounded', 'method': 'deterministic-v1',
              'explanation': '', 'reason': '', 'label': 'insufficient_context'}
    va, vb = a['value'], b['value']
    # Both temporal anchors must be evidenced before declaring a real disagreement.
    ta, tb = ca.get('period') or ca.get('as_of'), cb.get('period') or cb.get('as_of')
    missing = [k for k, v in context_diff.items() if not all(x is not None and x != '' for x in v)]
    if missing or not ta or not tb:
        result.update(reason='missing_context', explanation='Comparison needs supported context: ' + ', '.join(sorted(set(missing + ([] if ta and tb else ['time'])))) + '. Neither agreement nor conflict is established.')
        return result
    resolved_differences = {k: v for k, v in context_diff.items() if all(v)}
    value_equal = normalize(va['raw']).lower() == normalize(vb['raw']).lower()
    if va['kind'] == 'number' and vb['kind'] == 'number':
        na, ua = numeric(va)
        nb, ub = numeric(vb)
        result['calculation'] = {'left': str(na), 'right': str(nb), 'unit': ua, 'difference': str(nb - na)}
        if not ua or ua != ub:
            result.update(reason='unit_dimension', explanation='Units are missing or not known to be dimensionally equivalent. No numerical conflict is asserted.')
            return result
        if va.get('comparator', '=') != '=' or vb.get('comparator', '=') != '=':
            result.update(reason='qualified_bounds', explanation='At least one value is a bound. These claims do not establish identical exact values; bounds need separate interval reasoning.')
            return result
        pa, pb = va.get('precision'), vb.get('precision')
        tolerance = Decimal(0)
        if pa is not None and pb is not None:
            def resolution(v, precision):
                amount = Decimal(10) ** -precision * SCALES[v.get('scale', 'one')]
                return amount / 100 if key(v.get('unit') or '') in ('basis points', 'bps') else amount
            tolerance = max(resolution(va, pa), resolution(vb, pb)) / 2
        value_equal = na == nb or (tolerance > 0 and abs(na - nb) < tolerance)
        result['calculation']['rounding_tolerance'] = str(tolerance)
    elif va['kind'] == 'range' or vb['kind'] == 'range':
        result.update(reason='range_review', explanation='Range comparison requires interval semantics; the system abstains.')
        return result
    elif va['kind'] != vb['kind']:
        return None
    if resolved_differences:
        result.update(label='reconciles', reason='context_difference',
                      explanation='These assertions refer to different contexts: ' + '; '.join(f'{k}: {v[0]} versus {v[1]}' for k, v in resolved_differences.items()) + '. They do not establish a same-context contradiction. This explains comparability, not a causal explanation of the magnitude.')
    elif a.get('modality', 'asserted') != b.get('modality', 'asserted'):
        result.update(label='reconciles', reason='modality', explanation='One claim is qualified differently (for example, a forecast versus an assertion); they are not interchangeable observations.')
    elif value_equal and a.get('polarity', 'positive') == b.get('polarity', 'positive'):
        result.update(label='corroborates', reason='same_value', explanation='The subject, predicate and recorded context match. Values agree exactly or within the documented display precision after unit conversion. This is agreement between disclosures, not independent proof of truth.')
    elif a.get('polarity', 'positive') != b.get('polarity', 'positive') and not value_equal:
        result.update(reason='different_value_and_polarity', explanation='A negative assertion about one value does not contradict a positive assertion about a different value.')
    elif va['kind'] == 'number' and vb['kind'] == 'number':
        result.update(label='contradicts', certainty='likely', reason='different_values', explanation='The recorded subject, predicate, time and context match, but the numerical values disagree beyond display precision. An unrecorded qualification remains possible; neither source is declared correct.')
    elif value_equal and a.get('polarity') != b.get('polarity'):
        result.update(label='contradicts', certainty='likely', reason='opposing_polarity', explanation='Matching assertions and context have opposing explicit polarity. This is a likely contradiction.')
    else:
        # Generic address components, no company names or postal codes in runtime logic.
        za, zb = re.findall(r'\b\d{5,6}\b', va['raw']), re.findall(r'\b\d{5,6}\b', vb['raw'])
        stem_a = re.sub(r'\b\d{5,6}\b', '', key(va['raw']))
        stem_b = re.sub(r'\b\d{5,6}\b', '', key(vb['raw']))
        if za and zb and za[-1] != zb[-1] and SequenceMatcher(None, stem_a, stem_b).ratio() > .85:
            result.update(label='contradicts', certainty='likely', reason='address_postal_code', explanation=f'The address text and recorded context align, but postal codes differ: {za[-1]} versus {zb[-1]}. This may be a disclosure typo; the evidence does not establish which is correct.')
        else:
            result.update(reason='semantic_review', explanation='Different text does not necessarily mean mutually exclusive facts. Semantic review is needed.')
    return result


def pair_eligible(a, b):
    """Avoid turning a dated series inside one PDF into a dense relationship graph.

    Cross-document claims remain candidates because they can corroborate, conflict,
    or describe a revision. Within one document, rows with distinct explicit time
    anchors are separate events rather than an apparent contradiction. Timeless
    assertions remain candidates (for example, two address disclosures), as do
    claims with the same supported period or as-of date.
    """
    if a.get('document_id') != b.get('document_id'):
        return True
    left, right = a.get('context', {}), b.get('context', {})
    anchors = [(left.get(name), right.get(name)) for name in ('period', 'as_of')]
    known = [(x, y) for x, y in anchors if x or y]
    return not known or all(x and y and x == y for x, y in known)


def candidates(claim, collection_id, limit=30):
    # Exact subject blocks are intentional: aliases must be supported, not guessed.
    import json
    terms = re.findall(r'\w+', claim.get('canonical_predicate', claim['predicate']))[:12]
    query = ' OR '.join('"' + term.replace('"', '') + '"' for term in terms)
    found = db.rows('''SELECT c.* FROM claim_search f JOIN claims c ON c.id=f.id
                        WHERE claim_search MATCH ? AND c.collection_id=? AND c.subject=?
                        AND c.status='accepted' ORDER BY rank LIMIT ?''',
                    (query or '"none"', collection_id, key(claim['subject']), limit))
    return [dict(json.loads(r['data']), id=r['id'], document_id=r['document_id']) for r in found]


def relate_document(doc_id):
    import json
    new = db.rows("SELECT * FROM claims WHERE document_id=? AND status='accepted'", (doc_id,))
    count = 0
    for row in new:
        a = json.loads(row['data'])
        a['document_id'] = row['document_id']
        for b in candidates(a, row['collection_id']):
            if b['id'] == row['id']:
                continue
            if not pair_eligible(a, b):
                continue
            left, right = sorted([row['id'], b['id']])
            if db.one('SELECT id FROM relationships WHERE left_id=? AND right_id=?', (left, right)):
                continue
            verdict = compare(a, b) if left == row['id'] else compare(b, a)
            if verdict:
                db.execute('INSERT OR IGNORE INTO relationships VALUES(?,?,?,?,?,?)',
                           (db.uid(), row['collection_id'], left, right, verdict['label'], db.dumps(verdict)))
                count += 1
    return count
