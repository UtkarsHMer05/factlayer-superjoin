from copy import deepcopy

import pytest

from backend.factlayer.compare import compare, numeric, pair_eligible


def claim(number='100', **value):
    return {'subject': 'Example Ltd', 'predicate': 'revenue', 'value': {'kind': 'number', 'raw': number, 'number': number, 'unit': 'INR', 'scale': 'one', 'precision': 0, **value}, 'context': {'period': 'FY2024', 'scope': 'consolidated'}, 'modality': 'asserted', 'polarity': 'positive'}


def test_crore_million_rounding():
    a, b = claim('81415.38', scale='million', precision=2), claim('8142', scale='crore')
    r = compare(a, b)
    assert r['label'] == 'corroborates'
    assert r['calculation']['difference'] == '4620000.00'


def test_real_numeric_contradiction():
    r = compare(claim('100'), claim('120'))
    assert r['label'] == 'contradicts' and r['certainty'] == 'likely'


@pytest.mark.parametrize('field,other', [('period', 'FY2023'), ('scope', 'standalone'), ('vintage', 'second advance estimates')])
def test_context_reconciliation(field, other):
    a, b = claim(), claim('120')
    a['context'][field] = 'first advance estimates' if field == 'vintage' else a['context'][field]
    b['context'][field] = other
    assert compare(a, b)['label'] == 'reconciles'


def test_missing_scope_does_not_imply_equality():
    a, b = claim(), claim('120')
    del b['context']['scope']
    assert compare(a, b)['label'] == 'insufficient_context'


def test_shared_as_of_allows_one_side_to_record_an_extra_period_label():
    a, b = claim(), claim()
    a['context'] = {'as_of': 'March 31, 2024'}
    b['context'] = {'as_of': 'March 31, 2024', 'period': 'Q4 FY24'}
    assert compare(a, b)['label'] == 'corroborates'


def test_missing_time_abstains():
    a, b = claim(), claim()
    a['context'] = b['context'] = {}
    assert compare(a, b)['label'] == 'insufficient_context'


@pytest.mark.parametrize('field,other', [('subject', 'Other Ltd'), ('predicate', 'total income')])
def test_no_false_corroboration_for_different_claim(field, other):
    a, b = claim(), claim()
    b[field] = other
    assert compare(a, b) is None


def test_explicit_bound_is_not_exact_equality():
    assert compare(claim('100', comparator='>'), claim('100'))['label'] == 'insufficient_context'


def test_percent_and_percentage_points_are_distinct():
    assert compare(claim('2', unit='percent'), claim('200', unit='bps'))['label'] == 'insufficient_context'
    assert str(numeric(claim('-10', unit='bps')['value'])[0]) == '-0.1'


def test_postal_code_conflict():
    a = claim()
    a['predicate'] = 'corporate office address'
    a['value'] = {'kind': 'text', 'raw': 'Plot No. 7, Sector 12, Example City 110001'}
    b = deepcopy(a)
    b['value']['raw'] = 'Plot No. 7, Sector 12, Example City 110002'
    assert compare(a, b)['reason'] == 'address_postal_code'


def test_same_document_undated_postal_code_conflict_is_likely():
    a = claim()
    a.update(document_id='same-document', predicate='corporate office address',
             value={'kind': 'text', 'raw': 'Plot No. 7, Sector 12, Example City 110001'}, context={})
    b = deepcopy(a)
    b['value']['raw'] = 'Plot No. 7, Sector 12, Example City 110002'
    assert compare(a, b)['label'] == 'contradicts'


def test_registered_and_corporate_office_not_same_predicate():
    a, b = claim(), claim()
    a['predicate'] = 'registered office address'
    b['predicate'] = 'corporate office address'
    assert compare(a, b) is None


def test_negation():
    a = claim()
    a['predicate'] = 'permits remote work'
    a['value'] = {'kind': 'text', 'raw': 'remote work'}
    b = deepcopy(a)
    b['polarity'] = 'negative'
    assert compare(a, b)['reason'] == 'opposing_polarity'


def test_data_discovered_alias():
    a, b = claim(), claim()
    b['predicate'] = 'turnover'
    b['canonical_predicate'] = 'revenue'
    assert compare(a, b)['label'] == 'corroborates'


def test_basis_point_rounding_uses_converted_precision():
    assert compare(claim('100', unit='bps'), claim('101', unit='bps'))['label'] == 'contradicts'


def test_negating_one_value_does_not_contradict_another():
    a, b = claim('100'), claim('120')
    a['polarity'] = 'negative'
    assert compare(a, b)['label'] == 'insufficient_context'


def test_same_document_dated_series_is_not_a_relationship_candidate():
    a, b = claim(), claim('120')
    a.update(document_id='same')
    b.update(document_id='same')
    a['context']['as_of'] = '2024-01-01'
    b['context']['as_of'] = '2024-02-01'
    assert not pair_eligible(a, b)


def test_cross_document_dates_remain_comparison_candidates():
    a, b = claim(), claim('120')
    a.update(document_id='left')
    b.update(document_id='right')
    a['context']['as_of'] = '2024-01-01'
    b['context']['as_of'] = '2024-02-01'
    assert pair_eligible(a, b)
