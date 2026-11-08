from eyecare.core import monitors as m


def test_key_strips_device_prefix():
    assert m.key("\\\\.\\DISPLAY2") == "DISPLAY2"
    assert m.key("DISPLAY1") == "DISPLAY1"


def test_set_roundtrip_and_junk():
    assert m.parse_set("DISPLAY2, DISPLAY1 ,,") == {"DISPLAY1", "DISPLAY2"}
    assert m.format_set({"B", "A"}) == "A,B"
    assert m.parse_set("") == set()


def test_map_roundtrip_clamps_and_ignores_junk():
    assert m.parse_map("DISPLAY1=80;DISPLAY2=999;X=abc;=5;noeq") == {"DISPLAY1": 80, "DISPLAY2": 100}
    assert m.parse_map("D=1") == {"D": 30}
    assert m.parse_map(m.format_map({"B": 50, "A": 90})) == {"A": 90, "B": 50}
