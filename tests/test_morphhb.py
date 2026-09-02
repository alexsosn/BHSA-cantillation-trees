from xml.etree import ElementTree as ET

from bhsa_cantillation.morphhb import NS, accent_system, parse_verse

CATALOG = {
    "prose": {
        "conjunctive": {"\u05a5": {"name": "Merkha"}},
        "disjunctive": {"\u0591": {"name": "Atnach"}},
    },
    "poetic": {"conjunctive": {}, "disjunctive": {}},
}


def test_accent_system_handles_job_boundaries():
    assert accent_system("Job.2.13") == "prose"
    assert accent_system("Job.3.1") == "prose"
    assert accent_system("Job.3.2") == "poetic"
    assert accent_system("Job.42.6") == "poetic"
    assert accent_system("Job.42.7") == "prose"


def test_parse_verse_transfers_qere_path_to_ketiv():
    xml = f"""
    <verse xmlns="{NS[1:-1]}" osisID="Gen.1.1">
      <w type="x-ketiv" id="k1">אלהם</w>
      <note type="variant"><rdg type="x-qere"><w n="1">אֱלֹהִ֑ים</w></rdg></note>
    </verse>
    """
    parsed = parse_verse(ET.fromstring(xml), CATALOG)
    assert len(parsed) == 1
    assert parsed[0].consonants == "אלהם"
    assert parsed[0].path == "1"
    assert parsed[0].accent_name == "Atnach"


def test_parse_verse_uses_last_word_of_multiword_qere_for_path():
    xml = f"""
    <verse xmlns="{NS[1:-1]}" osisID="Ps.10.10">
      <w type="x-ketiv" id="k1">חלכאים</w>
      <note type="variant"><rdg type="x-qere">
        <w>חֵ֣יל</w><w n="0">כָּאִֽים</w>
      </rdg></note><seg type="x-sof-pasuq">׃</seg>
    </verse>
    """
    catalog = {
        **CATALOG,
        "poetic": {
            "conjunctive": {},
            "disjunctive": {"\u05c3": {"name": "Sof Pasuq"}},
        },
    }
    parsed = parse_verse(ET.fromstring(xml), catalog)
    assert parsed[0].text == "חֵ֣יל כָּאִֽים"
    assert parsed[0].path == "0"
    assert parsed[0].accent_marks == "ֽ׃"
    assert parsed[0].accent_name == "Sof Pasuq"
