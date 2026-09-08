"""Compact model-output mapping is deterministic: parse values before any claim is grounded."""
from backend.factlayer.config import settings
from backend.factlayer.model import _map_claim, _parse_number, _remote_body


def unit():
    return {'id': 'u1', 'text': 'source'}


def test_parse_number_variants():
    assert _parse_number('18,793') == ('18793', '=', 0)
    assert _parse_number('>33,200') == ('33200', '>', 0)
    assert _parse_number('over 400') == ('400', '>', 0)
    assert _parse_number('39.34%') == ('39.34', '=', 2)
    assert _parse_number('(1,053)') == ('-1053', '=', 0)
    assert _parse_number('₹500.40 million') == ('500.40', '=', 2)
    assert _parse_number('6.4 per cent') == ('6.4', '=', 1)
    assert _parse_number('25 basis points') == ('25', '=', 0)
    assert _parse_number('March 30, 2024') is None


def test_map_claim_number_with_scale_and_unit():
    claim, error = _map_claim({'subject': 'Example Ltd', 'predicate': 'revenue', 'value_raw': '8,142',
                               'quote': 'FY24 revenue was 8,142 crore', 'period': 'FY24', 'unit': '₹ Cr', 'scope': ''}, unit())
    assert error is None
    v = claim.value
    assert v.kind == 'number' and v.number == '8142' and v.scale == 'crore' and v.unit == 'inr'
    assert claim.context['period'] == 'FY24'
    assert claim.context_evidence['period'][0].quote == 'FY24'


def test_map_claim_percent_unit():
    claim, _ = _map_claim({'subject': 'India', 'predicate': 'gdp growth', 'value_raw': '6.4%',
                           'quote': 'growth of 6.4%', 'period': 'FY25', 'unit': 'per cent', 'scope': ''}, unit())
    assert claim.value.unit == 'percent' and claim.value.number == '6.4'


def test_map_claim_range_and_percentage_points():
    claim, _ = _map_claim({'subject': 'India', 'predicate': 'inflation range', 'value_raw': '4.2 to 4.8 percentage points',
                           'quote': 'Inflation is 4.2 to 4.8 percentage points in FY25.',
                           'period': 'FY25', 'unit': 'percentage points', 'scope': ''}, unit())
    assert claim.value.kind == 'range'
    assert (claim.value.number, claim.value.upper, claim.value.unit) == ('4.2', '4.8', 'percentage points')


def test_map_claim_preserves_explicit_polarity_and_modality():
    claim, _ = _map_claim({'subject': 'Example Ltd', 'predicate': 'will not open a site', 'value_raw': 'will not open',
                           'quote': 'Example Ltd forecasts it will not open a site in FY25.',
                           'period': 'FY25', 'unit': '', 'scope': '', 'polarity': 'negative', 'modality': 'forecast'}, unit())
    assert (claim.polarity, claim.modality) == ('negative', 'forecast')


def test_map_claim_text_preserves_address():
    raw = 'Plot No. 5, Sector 44, Gurugram, Haryana 122002'
    claim, _ = _map_claim({'subject': 'Example Ltd', 'predicate': 'corporate office address',
                           'value_raw': raw, 'quote': f'address {raw}', 'period': '', 'unit': '', 'scope': ''}, unit())
    assert claim.value.kind == 'text' and claim.value.raw == raw


def test_map_claim_rejects_empty_fields():
    claim, error = _map_claim({'subject': '', 'predicate': 'revenue', 'value_raw': '1', 'quote': 'x'}, unit())
    assert claim is None and error


def test_map_claim_scope_requires_quote_support():
    claim, _ = _map_claim({'subject': 'Example Ltd', 'predicate': 'revenue', 'value_raw': '100',
                           'quote': 'revenue was 100', 'period': 'FY24', 'unit': '', 'scope': 'consolidated'}, unit())
    assert 'scope' not in claim.context


def test_period_evidence_is_in_the_unit():
    """The worker grounds against [unit] so a context anchor must reference that unit id."""
    claim, _ = _map_claim({'subject': 'Example Ltd', 'predicate': 'revenue', 'value_raw': '100',
                           'quote': 'revenue was 100 in FY24', 'period': 'FY24', 'unit': '', 'scope': ''}, unit())
    assert claim.context_evidence['period'][0].unit_id == 'u1'


def test_map_claim_keeps_only_explicit_qualifiers():
    claim, _ = _map_claim({'subject': 'Example Ltd', 'predicate': 'growth', 'value_raw': '6.4%',
                           'quote': 'The first advance estimate projects growth of 6.4% in FY25.',
                           'period': 'FY25', 'unit': '%', 'scope': '',
                           'vintage': 'first advance estimate', 'status': 'projects',
                           'population': 'all residents'}, unit())
    assert claim.context == {'period': 'FY25', 'vintage': 'first advance estimate', 'status': 'projects'}
    assert set(claim.context_evidence) == set(claim.context)


def test_remote_request_uses_documented_top_level_thinking_control(monkeypatch):
    monkeypatch.setattr(settings, 'model', 'z-ai/glm-5.3-free')
    body = _remote_body('system', {'source': 'untrusted source'})
    assert body['thinking'] == {'type': 'disabled'}
    assert 'chat_template_kwargs' not in body
    assert body['stream'] is True
