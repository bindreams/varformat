# Varformat Library
Varformat can format and un-format (parse) strings containing various styles of variables.
```python
>>> import varformat as vf
>>> vf.format("Hi ${name}!", name="mom")
'Hi mom!'
>>> vf.parse("archive-${date}.tar.gz", "archive-1970-01-01.tar.gz")
{'date': '1970-01-01'}

>>> from varformat.formats import python
>>> python.format("Classic {style}", style="python braces")
'Classic python braces'

>>> from varformat.formats import posix_shell as sh
>>> sh.format("POSIX compliant $style", style="dollar variables")
'POSIX compliant dollar variables'

```

## Getting Started
Varformat is available to install via pip:
```
pip install varformat
```

When installed, the modules `varformat` and `varformat.formats` will be available. Global functions `format`, `vformat`, and `parse` represent the default formmatter with a `${}` style:
```python
>>> import varformat as vf
>>> vf.format("my name ${name}", name="jeff")
'my name jeff'

```

If it is necessary to specify keys which are not valid python identifiers, such as numbers or string with spaces, you can use `vformat` instead:
```python
>>> import varformat as vf
>>> vf.vformat("My three favorite foods: ${1}, ${2}, and ${1} again",
...     {"1": "pizza", "2": "chocolate"})
'My three favorite foods: pizza, chocolate, and pizza again'

```

`vformat` also supports keyword arguments to customize formatting behavior. `partial_ok` (default `False`) and `extra_ok` (default: `True`) control whether it is allowed to provide less (or more) arguments than the format string requires. `ambiguity_check` (default: `False`) will raise an error if your resulting string will be ambiguous:
```python
>>> import varformat as vf
>>> vf.vformat("package-${os}-${arch}", {"os": "ubuntu-22.04", "arch": "amd64"}, ambiguity_check=True)
Traceback (most recent call last):
...
varformat.AmbiguityError: refusing to format because parsing would be ambiguous:
  could be: {'os': 'ubuntu-22.04', 'arch': 'amd64'}
        or: {'os': 'ubuntu', 'arch': '22.04-amd64'}

```

The `parse` function, which performs the inverse of `vformat`, also supports `ambiguity_check` (default: `True`):
```python
>>> import varformat as vf
>>> vf.parse("package-${os}-${arch}", "package-ubuntu-22.04-amd64")
Traceback (most recent call last):
    ...
varformat.AmbiguityError: parsing is ambiguous:
  could be: {'os': 'ubuntu-22.04', 'arch': 'amd64'}
        or: {'os': 'ubuntu', 'arch': '22.04-amd64'}

```

You can of course set `ambiguity_check` to `False`, and `parse` will parse using the regular expression rules (greedily).

### Other formatters
Module `varformat.formats` contains formatters with other syntaxes:
- `varformat.formats.posix_shell` follows POSIX shell variable rules: it disallows numeric identifiers, identifiers with spaces, but allows referencing variables like `$var` in addition to `${var}`;
- `varformat.formats.python` follows classic python format string rules (e.g. `{var}`).

You can define your own formatter with your own custom syntax by subclassing either `varformat.RegexFormatter` and defining a regular expression that detects placeholders, or `varformat.AbstractFormatter` and defining a parsing function. See class docstrings for more information.
