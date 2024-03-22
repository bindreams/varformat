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
import itertools
import regex as re
from . import AbstractFormatter, RegexFormatter, _References

__all__ = ["permissive", "posix_shell", "python"]

permissive = RegexFormatter(r"\${([\w\s]+)}")
"""
Simple variables which use the dollar braces syntax and allow any string inside.

Used as a default engine in this package.
"""


class _PosixFormatter(AbstractFormatter):
    re_posix_variable_braces = re.compile(r"\${([a-zA-Z_]\w*)}")
    re_posix_variable_no_braces = re.compile(r"\$([a-zA-Z_]\w*)")

    def _references(self, fmtstring: str) -> _References:
        """Produce a map {var_name: [location, ...], ...} for a format string.
        See docstring for _References for more info.
        """
        result = {}

        for reference in itertools.chain(
            re.finditer(self.re_posix_variable_braces, fmtstring),
            re.finditer(self.re_posix_variable_no_braces, fmtstring),
        ):
            variable = reference[1]
            locations = result.get(variable, [])
            locations.append((reference.start(), reference.end()))
            result[variable] = locations

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
