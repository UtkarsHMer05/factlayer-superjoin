"""Layout-preserving source units. Coordinates always refer to the uploaded page."""
import hashlib
import re
import unicodedata

import pymupdf


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text).replace('\u00ad', '')).strip()


def normalized_with_offsets(text):
    chars, offsets = [], []
    for i, char in enumerate(text):
        for expanded in unicodedata.normalize('NFKC', char):
            if expanded == '\u00ad':
                continue
            if expanded.isspace():
                if chars and chars[-1] != ' ':
                    chars.append(' ')
                    offsets.append(i)
            else:
                chars.append(expanded)
                offsets.append(i)
    if chars and chars[-1] == ' ':
        chars.pop()
        offsets.pop()
    return ''.join(chars), offsets


def page_units(page, doc_id, number):
    words = page.get_text('words', sort=True)
    blocks = page.get_text('blocks', sort=True)
    width, height = page.rect.width, page.rect.height
    # Facing-page geometry plus independent footer page labels and a real center gutter.
    footer = [w for w in words if w[1] > height * .88 and re.fullmatch(r'\d{1,4}', w[4])]
    spread = (width > height * 1.25 and any(w[0] < width * .45 for w in footer)
              and any(w[0] > width * .55 for w in footer)
              and not any(w[0] < width / 2 - 3 and w[2] > width / 2 + 3 for w in words))
    regions = [pymupdf.Rect(0, 0, width / 2, height), pymupdf.Rect(width / 2, 0, width, height)] if spread else [page.rect]
    units, warnings = [], []
    display_numbers = [s for b in page.get_text('dict')['blocks'] if 'lines' in b
                       for line in b['lines'] for s in line['spans'] if s['size'] >= 18 and re.search(r'\d', s['text'])]
    visual_numeric_risk = len(display_numbers) >= 4
    for ri, region in enumerate(regions):
        region_blocks = [b for b in blocks if b[6] == 0 and region.contains(pymupdf.Rect(b[:4]))]
        if not region_blocks:
            region_blocks = [b for b in blocks if b[6] == 0 and region.intersects(pymupdf.Rect(b[:4]))]
        region_words = [w for w in words if region.contains(pymupdf.Rect(w[:4]))]
        # Individual lines with word spans retain exact quote->word provenance even in tables.
        lines = {}
        for w in region_words:
            lines.setdefault((w[5], w[6]), []).append(w)
        # Preserve paragraph blocks before ordering their lines: sorting all lines by y
        # interleaves two-column prose and can attach one company's action to another.
        block_order = {b[5]: i for i, b in enumerate(sorted(region_blocks, key=lambda b: (b[1], b[0])))}
        ordered = sorted(lines.values(), key=lambda line: (block_order.get(line[0][5], 100000), line[0][6]))
        text, spans = '', []
        for line in ordered:
            for w in sorted(line, key=lambda v: v[0]):
                if text and not text.endswith('\n'):
                    text += ' '
                start = len(text)
                text += w[4]
                spans.append({'start': start, 'end': len(text), 'box': list(w[:4])})
            text += '\n'
        if not text.strip():
            continue
        # Bound units at line boundaries without dropping any source characters.
        start = 0
        while start < len(text):
            end = min(start + 10000, len(text))
            if end < len(text):
                boundary = text.rfind('\n', start + 4000, end)
                if boundary > start:
                    end = boundary + 1
            segment = text[start:end]
            unit_spans = [dict(s, start=s['start'] - start, end=s['end'] - start) for s in spans if s['start'] >= start and s['end'] <= end]
            uid = hashlib.sha256(f'{doc_id}:{number}:{ri}:{start}'.encode()).hexdigest()[:32]
            normalized, offsets = normalized_with_offsets(segment)
            units.append({'id': uid, 'page': number, 'region': ri, 'text': segment,
                          'normalized': normalized, 'offsets': offsets, 'spans': unit_spans,
                          'box': list(region), 'method': 'native_text', 'visual_numeric_risk': visual_numeric_risk,
                          'printed_labels': [w[4] for w in footer if region.contains(pymupdf.Rect(w[:4]))]})
            start = end
    char_count = sum(len(u['text']) for u in units)
    if char_count < 100:
        warnings.append('Low text coverage: cover, divider, image or scan; semantic extraction may be incomplete.')
    if visual_numeric_risk:
        warnings.append('Infographic/chart numbers require visual verification. Numeric claims from this layout are quarantined by the text-only pipeline.')
    # Numbers scattered across short blocks are a layout risk, not proof of a chart.
    numerical = sum(bool(re.search(r'\d', b[4])) and len(b[4]) < 180 for b in blocks if b[6] == 0)
    if width > height and not spread and numerical >= 8:
        warnings.append('Dense visual layout: chart labels and values require region-level verification; native text order is not sufficient.')
    return {'width': width, 'height': height, 'rotation': page.rotation,
            'spread': spread, 'characters': char_count, 'warnings': warnings, 'units': units}


def locate(anchor, units):
    unit = next((u for u in units if u['id'] == anchor.unit_id), None)
    if unit is None:
        raise ValueError('Evidence refers to an unknown unit')
    needle = normalize(anchor.quote)
    haystack, mapping = normalized_with_offsets(unit['text'])
    start = haystack.find(needle)
    if start < 0:
        raise ValueError(f'Quote is absent from source: {anchor.quote[:100]}')
    repeated = haystack.find(needle, start + 1) >= 0
    if repeated and anchor.role == 'value':
        raise ValueError('Value quote is ambiguous; include its full row')
    a, b = mapping[start], mapping[start + len(needle) - 1] + 1
    boxes = [s['box'] for s in unit['spans'] if s['end'] > a and s['start'] < b]
    return {'unit_id': unit['id'], 'quote': unit['text'][a:b], 'role': anchor.role,
            'page': unit['page'], 'start': a, 'end': b, 'boxes': boxes,
            'method': unit['method'], 'repeated_text': repeated}


def ground(claim, units):
    anchors = [locate(a, units) for a in claim.evidence]
    context = {}
    for key, value in claim.context.items():
        if value is None:
            continue
        sources = claim.context_evidence.get(key, [])
        if not sources:
            raise ValueError(f'Context {key} has no supporting evidence')
        context[key] = [locate(a, units) for a in sources]
        source_context = normalize(' '.join(a['quote'] for a in context[key])).lower()
        if key == 'scope' and value.lower() not in source_context:
            raise ValueError('Scope value is not explicitly supported by its cited context')
        if key == 'period' and re.search(r'\bQ[1-4]\b', source_context, re.IGNORECASE) and not re.search(r'\bQ[1-4]\b', value, re.IGNORECASE):
            raise ValueError('Period drops a quarter qualifier present in the cited source')
    # Numeric token must occur in the evidence; never accept value hallucinations.
    corpus = normalize(' '.join(a['quote'] for a in anchors))
    if claim.value.kind in ('number', 'range'):
        cited = {a.unit_id for a in claim.evidence}
        if any(u.get('visual_numeric_risk') and u['id'] in cited for u in units):
            raise ValueError('Visual layout: numeric infographic/chart claims require visual verification')
        token = claim.value.number.replace(',', '')
        if not re.search(r'(?<![\d.])' + re.escape(token) + r'(?![\d.])', corpus.replace(',', '')):
            raise ValueError('Numeric value is not present in the cited evidence')
    elif normalize(claim.value.raw).lower() not in corpus.lower():
        raise ValueError('Text value is not present in the cited evidence')
    roles = {a['role'] for a in anchors}
    if not (roles & {'assertion', 'header'}):
        raise ValueError('A value alone does not ground a predicate; cite its assertion or header')
    result = claim.model_dump()
    result['anchors'] = anchors
    result['context_anchors'] = context
    result['grounding'] = 'source_spans_verified'
    result['grounding_limit'] = 'Exact source spans and value checked; semantic interpretation is model-generated, not independently proven.'
    return result
