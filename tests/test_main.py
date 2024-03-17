import pytest
import dollarvar as dv

def roundtrip(fmtstring, args, result):
    actual = dv.vformat(fmtstring, args)
    assert actual == result
    assert dv.parse(fmtstring, actual) == args

def test_basic():
    assert dv.format(">${var}<", var=1) == ">1<"
    assert dv.format("${a}+${b}=${c}", a=1, b=2, c=3) == "1+2=3"

    assert dv.format("hello world") == "hello world"
    assert dv.format("") == ""

    assert dv.vformat(">${var}<", {"var": 1}) == ">1<"
    assert dv.vformat("${a}+${b}=${c}", {"a": 1, "b": 2, "c": 3}) == "1+2=3"

    assert dv.vformat("hello world", {}) == "hello world"
    assert dv.vformat("", {}) == ""

def test_var_syntax():
    assert dv.vformat("${a}", {"a": 1}) == "1"
    assert dv.vformat("${A}", {"A": 1}) == "1"
    assert dv.vformat("${1}", {"1": 1}) == "1"
    assert dv.vformat("${var space}", {"var space": 1}) == "1"
    assert dv.vformat("${_}", {"_": 1}) == "1"

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
    roundtrip("${a}-${b}-${c}", {"a": "a", "b": "b", "c": "c"}, "a-b-c")
