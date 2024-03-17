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
>>> sh.format("POSIX compliant ${style}", style="dollar variables")
'POSIX compliant dollar variables'

```
