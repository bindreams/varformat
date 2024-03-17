import pytest
import dollarvar as dv
from dollarvar.formats import posix_shell as sh, python as py


def roundtrip(engine, fmtstring, args, result):
    actual = engine.vformat(fmtstring, args)
    assert actual == result
    assert engine.parse(fmtstring, actual) == args


def test_basic():
    assert dv.format(">${var}<", var=1) == ">1<"
    assert dv.format("${a}+${b}=${c}", a=1, b=2, c=3) == "1+2=3"

    assert dv.format("hello world") == "hello world"
    assert dv.format("") == ""

    assert dv.vformat(">${var}<", {"var": 1}) == ">1<"
    assert dv.vformat("${a}+${b}=${c}", {"a": 1, "b": 2, "c": 3}) == "1+2=3"

    assert dv.vformat("hello world", {}) == "hello world"
    assert dv.vformat("", {}) == ""


def test_missing():
    with pytest.raises(KeyError, match="missing"):
        dv.format("${present} ${missing}", present="present")

    assert dv.vformat("${present} ${missing}", {"present": "present"}, partial_ok=True) == "present ${missing}"

    with pytest.raises(KeyError, match="missing"):
        dv.vformat("${present} ${missing}", {"present": "present"})


def test_extra():
    assert dv.format("${a}+${a}=${a}", a=1, b=2, c=3) == "1+1=1"
    assert dv.vformat("${a}+${a}=${a}", {"a": 1, "b": 2, "c": 3}) == "1+1=1"

    assert dv.format("", x=1) == ""
    assert dv.vformat("", {"x": 1}) == ""

    with pytest.raises(ValueError, match="unused arguments: b, c"):
        dv.vformat("${a}", {"a": True, "b": False, "c": False}, extra_ok=False)


def test_parse():
    assert dv.parse(">${var}<", ">1<") == {"var": "1"}
    assert dv.parse("${a} ${b}", "1 2") == {"a": "1", "b": "2"}


def test_roundtrip():
    roundtrip(dv, "${a} ${b} ${c}", {"a": "a", "b": "b", "c": "c"}, "a b c")


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
