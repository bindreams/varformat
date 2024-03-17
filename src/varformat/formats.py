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
from . import FormatEngine

permissive = FormatEngine(r"\${([\w\s]+)}")
"""
Simple variables which use the dollar braces syntax and allow any string inside.

Used as a default engine in this package.
"""

posix_shell = FormatEngine(r"\${([a-zA-Z_]\w*)}")
"""
POSIX shell-style variables.

See https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap03.html#tag_03_235
"""

python = FormatEngine(r"{([[:alpha:]_]\w*)}")
"""
Python curly braces with python-style identifiers.

See https://docs.python.org/3/reference/lexical_analysis.html#identifiers
"""
