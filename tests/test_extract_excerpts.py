from lxml import etree

from extract_excerpts import compute_location_for_seg


def test_compute_location_range():
    seg_str = '''<seg xmlns="http://www.tei-c.org/ns/1.0" type="excerpt" xml:id="ex050232025-05-2016-20-32" status="reviewed"><lb n="1a1"/>༅ || na mo g+hu ru | <rs type="person" ana="corpusmd:named_reference" ref="db:3745">mkhas pa chen po dpal mar me mdzad <abbr>ye shes</abbr></rs> kyis sde snod kyi chos <abbr>thams cad</abbr> kyi don bsdus ste bsgoM pa ni dbu ma'i man ngag 'di yin te | thog mar 'khor das <lb n="1a2"/> kyi chos kun rdzob du bden pas stong pa'i rten 'brel rgyu 'bras mi slu ba sgyu ma lta bu dang | don spros bral naM mkha'i dkyil ltar stong pa nyid du thos bsaM gyis thag chod par byas la | bsgoM ba'i
    <lb n="1a3"/> dus su sbyor dngos rjes 3 gyis <abbr>nyams su</abbr> blang ste |</seg>'''

    seg = etree.fromstring(seg_str)
    assert compute_location_for_seg(seg) == "1a1 - 1a3"


def test_preceding_lb_used_when_seg_starts_with_text():
    doc = '''<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <lb n="10"/>
    <seg type="excerpt" xml:id="s1">This starts text <lb n="11"/> more text</seg>
    </TEI>'''
    tree = etree.fromstring(doc)
    seg = tree.xpath('//tei:seg', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]
    assert compute_location_for_seg(seg) == "10 - 11"


def test_preceding_lb_used_when_seg_starts_with_milestone():
    doc = '''<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <lb n="20"/>
    <seg type="excerpt" xml:id="s2"><milestone unit="section" n="X"/><lb n="21"/>content</seg>
    </TEI>'''
    tree = etree.fromstring(doc)
    seg = tree.xpath('//tei:seg', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]
    # Milestone should not count as textual content before the first internal
    # <lb>, so the start should be the internal <lb> (21).
    assert compute_location_for_seg(seg) == "21"


def test_no_lbs_returns_empty():
    doc = '''<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <seg type="excerpt" xml:id="s3">no line breaks here</seg>
    </TEI>'''
    tree = etree.fromstring(doc)
    seg = tree.xpath('//tei:seg', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]
    assert compute_location_for_seg(seg) == ""


def test_single_lb_returns_single_n():
    seg = etree.fromstring('<seg xmlns="http://www.tei-c.org/ns/1.0"><lb n="5"/></seg>')
    assert compute_location_for_seg(seg) == "5"


def test_group_ranges_by_edref_with_preceding_lb():
    doc = '''<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <lb n="1b4" edRef="inst:5591"/>
    <seg type="excerpt" xml:id="s4">prefix text <lb n="1b1" edRef="inst:5591"/> <lb n="1b2" edRef="inst:5591"/> <lb n="2a1" edRef="inst:OTHER"/> <lb n="2a2" edRef="inst:OTHER"/></seg>
    </TEI>'''
    tree = etree.fromstring(doc)
    seg = tree.xpath('//tei:seg', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]
    assert compute_location_for_seg(seg) == "1b4 - 1b2; 2a1 - 2a2"
