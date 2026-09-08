import pymupdf
import pytest

from backend.factlayer.pdf import ground, locate, page_units
from backend.factlayer.schema import Anchor, Claim


def make_pdf(text='Example Ltd revenue: 100 INR in FY2024.'):
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((40, 50), text)
    return doc


def candidate(units):
    return Claim(subject='Example Ltd', predicate='revenue', assertion='Example Ltd revenue is 100 INR.',
                 value={'kind': 'number', 'number': '100', 'raw': '100', 'unit': 'INR'},
                 context={'period': 'FY2024'},
                 context_evidence={'period': [{'unit_id': units[0]['id'], 'quote': 'in FY2024.', 'role': 'context'}]},
                 evidence=[{'unit_id': units[0]['id'], 'quote': 'Example Ltd revenue: 100 INR in FY2024.', 'role': 'assertion'}])


def test_source_coordinates_and_quote_roundtrip():
    doc = make_pdf()
    units = page_units(doc[0], 'doc', 1)['units']
    result = ground(candidate(units), units)
    anchor = result['anchors'][0]
    assert anchor['boxes'] and anchor['page'] == 1
    assert units[0]['text'][anchor['start']:anchor['end']] == anchor['quote']


def test_hallucinated_quote_rejected():
    doc = make_pdf()
    units = page_units(doc[0], 'doc', 1)['units']
    c = candidate(units)
    c.evidence[0].quote = 'Revenue grew to 200.'
    with pytest.raises(ValueError, match='absent'):
        ground(c, units)


def test_value_not_supported_rejected():
    doc = make_pdf()
    units = page_units(doc[0], 'doc', 1)['units']
    c = candidate(units)
    c.value.number = '200'
    with pytest.raises(ValueError, match='Numeric value'):
        ground(c, units)


def test_context_requires_own_evidence():
    doc = make_pdf()
    units = page_units(doc[0], 'doc', 1)['units']
    c = candidate(units)
    c.context['scope'] = 'consolidated'
    with pytest.raises(ValueError, match='Context scope'):
        ground(c, units)


def test_address_commas_preserved():
    doc = make_pdf('Corporate address: Plot 7, Sector 12, Example City 110001')
    units = page_units(doc[0], 'doc', 1)['units']
    c = Claim(subject='Example Ltd', predicate='corporate address', assertion='Company has a corporate address',
              value={'kind': 'text', 'raw': 'Plot 7, Sector 12, Example City 110001'},
              evidence=[{'unit_id': units[0]['id'], 'quote': units[0]['text'].strip()}])
    assert ground(c, units)['anchors']


def test_two_column_paragraphs_do_not_interleave():
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=800)
    page.insert_textbox(pymupdf.Rect(30, 50, 270, 170), 'Alpha operates a delivery network.\nIts headquarters are in A city.')
    page.insert_textbox(pymupdf.Rect(310, 50, 570, 170), 'Beta supplies software.\nIts headquarters are in B city.')
    text = page_units(page, 'doc', 1)['units'][0]['text']
    assert 'Alpha operates a delivery network.\nIts headquarters are in A city.' in text


def test_landscape_slide_not_split_without_page_footers():
    doc = pymupdf.open()
    page = doc.new_page(width=960, height=540)
    page.insert_text((50, 50), 'Operations summary')
    assert page_units(page, 'd', 1)['spread'] is False


def test_spread_detected_with_two_footer_labels():
    doc = pymupdf.open()
    page = doc.new_page(width=1190, height=842)
    page.insert_text((40, 70), 'Left page')
    page.insert_text((650, 70), 'Right page')
    page.insert_text((40, 810), '60')
    page.insert_text((1100, 810), '61')
    result = page_units(page, 'd', 1)
    assert result['spread'] and len({u['region'] for u in result['units']}) == 2


def test_untrusted_unit_id_rejected():
    with pytest.raises(ValueError, match='unknown unit'):
        locate(Anchor(unit_id='invented', quote='100'), [])
