"""Extra variable formatters for varformat.

Import a formatting engine of your choice from this module and use its member functions `format`, `vformat`, and
`parse` in the same way you would use global function from the module.

Examples:
```
>>> from varformat.formats import python
>>> python.format("Hello {var}!", var="python")
'Hello python!'

>>> from varformat.formats import posix_shell as sh
>>> sh.format("Hello ${var}!", var="bash")
'Hello bash!'

```
"""

# pylint: disable=cyclic-import
from . import AbstractFormatter, RegexFormatter, _References

__all__ = ["permissive", "posix_shell", "python"]

permissive = RegexFormatter(r"\${([\w\s]+)}")
"""
Simple variables which use the dollar braces syntax and allow any string inside.

Used as a default engine in this package.
"""


class _PosixFormatter(AbstractFormatter):
    _formatter_braces = RegexFormatter(r"\${([a-zA-Z_]\w*)}")
    _formatter_no_braces = RegexFormatter(r"\$([a-zA-Z_]\w*)")

    def _references(self, fmtstring: str) -> _References:
        part1 = self._formatter_braces._references(fmtstring)  # pylint: disable=protected-access
        part2 = self._formatter_no_braces._references(fmtstring)  # pylint: disable=protected-access

        result_keys = part1.keys() | part2.keys()
        result = {k: part1.get(k, []) + part2.get(k, []) for k in result_keys}

        return result


posix_shell = _PosixFormatter()
"""
POSIX shell-style variables.

See https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap03.html#tag_03_235
"""

python = RegexFormatter(r"{([[:alpha:]_]\w*)}")
"""
Python curly braces with python-style identifiers.

See https://docs.python.org/3/reference/lexical_analysis.html#identifiers
"""
