import pytest
import varformat as vf
from varformat.formats import posix_shell as sh, python as py


def roundtrip(engine, fmtstring, args, result):
    actual = engine.vformat(fmtstring, args)
    assert actual == result
    assert engine.parse(fmtstring, actual) == args


def test_basic():
    assert vf.format(">${var}<", var=1) == ">1<"
    assert vf.format("${a}+${b}=${c}", a=1, b=2, c=3) == "1+2=3"

    assert vf.format("hello world") == "hello world"
    assert vf.format("") == ""

    assert vf.vformat(">${var}<", {"var": 1}) == ">1<"
    assert vf.vformat("${a}+${b}=${c}", {"a": 1, "b": 2, "c": 3}) == "1+2=3"

    assert vf.vformat("hello world", {}) == "hello world"
    assert vf.vformat("", {}) == ""


def test_missing():
    with pytest.raises(KeyError, match="missing"):
        vf.format("${present} ${missing}", present="present")

    assert vf.vformat("${present} ${missing}", {"present": "present"}, partial_ok=True) == "present ${missing}"

    with pytest.raises(KeyError, match="missing"):
        vf.vformat("${present} ${missing}", {"present": "present"})


def test_extra():
    assert vf.format("${a}+${a}=${a}", a=1, b=2, c=3) == "1+1=1"
    assert vf.vformat("${a}+${a}=${a}", {"a": 1, "b": 2, "c": 3}) == "1+1=1"

    assert vf.format("", x=1) == ""
    assert vf.vformat("", {"x": 1}) == ""

    with pytest.raises(ValueError, match="unused arguments: b, c"):
        vf.vformat("${a}", {"a": True, "b": False, "c": False}, extra_ok=False)


def test_parse():
    assert vf.parse(">${var}<", ">1<") == {"var": "1"}
    assert vf.parse("${a} ${b}", "1 2") == {"a": "1", "b": "2"}


def test_roundtrip():
    roundtrip(vf, "${a} ${b} ${c}", {"a": "a", "b": "b", "c": "c"}, "a b c")


def test_shell_engine():
    roundtrip(sh, "${a}", {"a": "a"}, "a")
    roundtrip(sh, "${A}", {"A": "a"}, "a")
    roundtrip(sh, "${_}", {"_": "a"}, "a")

    assert sh.vformat("${1}", {"1": "a"}) == "${1}"
    assert sh.vformat("${1a}", {"1": "a"}) == "${1a}"
    assert sh.vformat("${var space}", {"var space": "a"}) == "${var space}"
    assert sh.vformat("${юникод}", {"юникод": "a"}) == "${юникод}"


def test_python_engine():
    roundtrip(py, "{a}", {"a": "a"}, "a")
    roundtrip(py, "{A}", {"A": "a"}, "a")
    roundtrip(py, "{asd}", {"asd": "a"}, "a")
    roundtrip(py, "{_}", {"_": "a"}, "a")
    roundtrip(py, "{_1}", {"_1": "a"}, "a")
    roundtrip(py, "{asd1}", {"asd1": "a"}, "a")
    roundtrip(py, "{юникод}", {"юникод": "a"}, "a")

    assert py.vformat("{1}", {"1": "a"}) == "{1}"
    assert py.vformat("{1a}", {"1a": "a"}) == "{1a}"
    assert py.vformat("{var space}", {"var space": "a"}) == "{var space}"
