# Copyright 2023-2024 andreasxp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Format and parse string the dollar style `${variables}`.
This package exposes the following functions:
- `format()`: very similar to `str.format`. Simple formatting from keyword arguments.
- `vformat()`: takes a dict instead of keyword arguments, and allows other options for more configuration.
- `parse()`: un-format a formatted string and get back the arguments that were used.

See docstrings for the functions for more information.
"""
import io
from typing import Iterable, TypeAlias, Any
import itertools

import regex as re


__all__ = ["AmbiguityError", "FormatEngine", "format", "vformat", "parse"]


# Exceptions ===========================================================================================================
class AmbiguityError(ValueError):
    """This exception is raised when either:
    1. Parsing a string is ambiguous, i.e. has more than one valid parsing
    2. Formatting a string would produce a result that could not be unambiguously parsed later.

    An example of an ambiguous parsing would be `parse("${A} ${B}", "1 2 3")`, with two possible results:
    1. `A: "1", B: "2 3"`
    2. `A: "1 2", B: "3"`
    """

    def __init__(self, message, possibilities: Iterable[dict]):
        compiled_message = io.StringIO()
        compiled_message.write(message)

        prefix = "\n  could be: "
        for possibility in possibilities:
            compiled_message.write(prefix)
            compiled_message.write(str(possibility))
            prefix = "\n        or: "

        super().__init__(compiled_message.getvalue())


# Internals ============================================================================================================
_Location: TypeAlias = tuple[int, int]
"""A pair of indexes (begin, past-the-end) that specify a substring."""

_References: TypeAlias = dict[str, list[_Location]]
"""A mapping of variable names to a list of locations where these variable names should be replaced with values.
Example:
"${A}-${B}-${A}" has references:
    "A": [(0, 4), (10, 14)],
    "B": [(5, 9)]
"""

_Replacement: TypeAlias = tuple[_Location, str, Any]
"""All info needed for a single replacement:
1. Location of the text to be replaced (i.e. the substring "${VAR}")
2. Variable name (for error messages, etc.)
3. Replacement object (a string or something printable)
"""


class FormatEngine:
    """An engine that supports parsing and formatting using a particular style.

    `FormatEngine` provides three user-facing functions: `format`, `vformat`, and `parse`.

    For most usecases, you can either use the default engine (module-level functions `format`, `vformat`, and `parse`),
    import a special pre-packaged engine from `varformat.formats`, or create your own.

    See `__init__()` docstring for more info about creating your own engine.
    """

    def __init__(self, variable_regex):
        r"""Create an instance of `FormatEngine`.

        Supply a regular expression that would match your style of variable as `variable_regex`. The first group in that
        regex should capture the name of the variable. For example, the regex `\${([\w\s]+)}` matches dollar-style
        variables like `${var}`, and capture group 1 returns the name of the variable `var`.
        """
        self.re_variable = re.compile(variable_regex)

    def _references(self, fmtstring: str) -> _References:
        """Produce a map {var_name: [location, ...], ...} for a format string.
        See docstring for _References for more info.
        """
        result = {}

        for reference in re.finditer(self.re_variable, fmtstring):
            variable = reference[1]
            locations = result.get(variable, [])
            locations.append((reference.start(), reference.end()))
            result[variable] = locations

        return result

    def _replacements(
        self, references: _References, args: dict[str, Any], *, partial_ok, extra_ok
    ) -> list[_Replacement]:
        """Given a list of references and arguments, produce a list of replacements, sorted by their order in the
        string.

        See docstring for _Replacement for more info.
        """
        result = []
        args = dict(args)

        for name, locations in references.items():
            try:
                replacement = args.pop(name)
            except KeyError:
                if partial_ok:
                    continue
                raise

            result.extend((location, name, replacement) for location in locations)

        if not extra_ok and len(args) > 0:
            raise ValueError(f"unused arguments: {', '.join(args.keys())}")

        result.sort(key=lambda x: x[0][0])
        return result

    def _ambiguity_check(self, lhs_name, lhs_text, rhs_name, rhs_text, intermediate, message):
        """Performs an ambiguity check during format for a pair of sequential variables.

        Ambiguity checks are performed on pairs of variables that are next to each other because ambiguities arise when
        one of the two neighboring arguments contains the entire contents of the text that is inbetween. For example,
        for a format string `${A}-${B}`, if the replacement text for either A or B contains a dash `-`, then the
        resulting text would contain two dashes and parsing would be ambiguous.

        :param lhs_name: name of the left side variable
        :param lhs_text: text of the left side variable
        :param rhs_name: name of the right side variable
        :param rhs_text: text of the right side variable
        :param intermediate: unformatted text between variables
        """
        i = rhs_text.find(intermediate)
        if i != -1:
            raise AmbiguityError(
                message,
                [
                    {lhs_name: lhs_text, rhs_name: rhs_text},
                    {
                        lhs_name: lhs_text + intermediate + rhs_text[:i],
                        rhs_name: rhs_text[i + len(intermediate) :],
                    },
                ],
            )

        i = lhs_text.find(intermediate)
        if i != -1:
            raise AmbiguityError(
                message,
                [
                    {lhs_name: lhs_text, rhs_name: rhs_text},
                    {
                        lhs_name: lhs_text[:i],
                        rhs_name: lhs_text[i + len(intermediate) :] + intermediate + rhs_text,
                    },
                ],
            )

    def _format_iter(self, fmtstring: str, replacements: list[tuple[tuple[int, int], str, str]]):
        """Yields parts of the output string.

        Yield value types alternate between `str` (non-formatted in-between text, even if empty) and tuple[str, str]
        (variable name and the corresponding text replacement). Starts with `str` and ends with `str`.

        For a format string "Hello ${A} Goodbye ${B}" will yield:
        - `"Hello "`
        - `("A", ...)`
        - `" Goodbye "`
        - `("B", ...)`
        - `""`

        If the format string is empty, will generate a single empty `str`.
        """
        prev_end = 0

        for location, name, replacement_val in replacements:
            yield fmtstring[prev_end : location[0]]
            yield (name, str(replacement_val))

            prev_end = location[1]

        yield fmtstring[prev_end:]

    # Public Functions =================================================================================================
    def format(self, fmtstring: str, /, **kwargs) -> str:
        """Format a string, with replacements passed as keyword arguments.

        `format` function is not configurable, but if you need more functionality, such as permitting partially
        formatted results, forbidding unused arguments, or checking for ambiguous results, check out `vformat()`.

        Examples:
        ```
        >>> format("Hello ${name}!", name="Anna")
        'Hello Anna!'
        >>> format("${number} * 1 = ${number}", number=5)
        '5 * 1 = 5'
        >>> format("${name} ${surname}", name="John", surname="Doe", age=35)  # Extra argument ignored
        'John Doe'
        >>> format("Where is ${Kevin}?")
        Traceback (most recent call last):
            ...
        KeyError: Kevin

        ```
        """
        return self.vformat(fmtstring, kwargs)

    def vformat(
        self,
        fmtstring: str,
        /,
        args: dict,
        *,
        partial_ok=False,
        extra_ok=True,
        ambiguity_check=False,
    ) -> str:
        """Format a string, with replacements passed as a dictionary.

        Unlike `format()`, this function supports additional flags that control its behavior:
        - If `partial_ok` is set to `True`, strings are allowed to be partially formatted (default: `False`).
        - If `extra_ok` is set to `True` (the default), extra unused arguments are allowed.
        - If `ambiguity_check` is set to `True`, the function will fail if the result it produces could not be
        unambiguously parsed to get the arguments back. See also `parse()`.

        Examples:
        ```
        >>> vformat("Hello ${name}!", {"name": "Anna"})
        'Hello Anna!'
        >>> vformat("Partial parsing: ${A} ${B}", {"A": 1}, partial_ok=True)
        'Partial parsing: 1 ${B}'
        >>> vformat("No extras! ${var}", {"var": 1, "extra": 2}, extra_ok=False)
        Traceback (most recent call last):
            ...
        ValueError: unused arguments: extra
        ```
        """
        references = self._references(fmtstring)
        replacements = self._replacements(references, args, partial_ok=partial_ok, extra_ok=extra_ok)

        result = io.StringIO()
        iterator = iter(self._format_iter(fmtstring, replacements))

        name_last = None
        replacement_last = None
        try:
            while True:
                intermediate = next(iterator)
                result.write(intermediate)

                name, replacement = next(iterator)
                result.write(replacement)

                if ambiguity_check and name_last is not None:
                    self._ambiguity_check(
                        name_last,
                        replacement_last,
                        name,
                        replacement,
                        intermediate,
                        message="refusing to format because parsing would be ambiguous:",
                    )

                name_last = name
                replacement_last = replacement
        except StopIteration:
            pass

        return result.getvalue()

    def parse(self, fmtstring: str, /, string: str, *, ambiguity_check=True) -> dict[str, str] | None:
        """Parse (aka un-format) a string and return a mapping of variable names to their values, or `None` if the
        string did not match the pattern.

        By default, parsing will raise an `AmbiguityError` if the string could be successfully parsed in multiple ways.
        If `ambiguity_check` is set to `False`, the string will be passed using regex eager rules. For example, for a
        pattern `${A} ${B}`, an ambiguous string `1 2 3` would be parsed as `A: "1 2", B: "3"`.

        To avoid ambiguous strings, consider setting `ambiguity_check` to `True` when formatting with `vformat`.

        Examples:
        ```
        >>> parse("Hello ${name}!", "Hello Anna!")
        {'name': 'Anna'}
        >>> parse("Model-${X}-${Y}", "This does not match at all...")
        >>> parse("Model-${X}-${Y}", "Model-X1-155-91")
        Traceback (most recent call last):
            ...
        AmbiguityError: parsing is ambiguous:
        could be: {'X': 'X1-155', 'Y': '91'}
                or: {'X': 'X1', 'Y': '155-91'}
        >>> parse("Model-${X}-${Y}", "Model-X1-155-91", ambiguity_check=False)
        {'X': 'X1-155', 'Y': '91'}

        ```
        """
        references = self._references(fmtstring)
        args = {}

        # Compose a regular expression which would parse the source string
        for name, i in zip(references, itertools.count()):
            # Variables will be replaced by a named regex group "_N" where N is the index of the variable in references.
            # Named regex groups are needed because a single variable may appear multiple times and must match the same
            # text each time.
            args[name] = f"(?P<_{i}>.*)"

        replacements = self._replacements(references, args, partial_ok=False, extra_ok=False)

        # a list of [unformatted text, variable name, unformatted text, ...] for ambiguity checking later.
        dissection = []

        # Resulting regular expression with named capture groups in place of dollar variables
        regex = io.StringIO()
        iterator = iter(self._format_iter(fmtstring, replacements))
        try:
            while True:
                intermediate = next(iterator)
                dissection.append(intermediate)
                regex.write(re.escape(intermediate))  # Regex-escape intermediate text

                name, replacement = next(iterator)
                dissection.append(name)
                regex.write(replacement)
        except StopIteration:
            pass

        match = re.fullmatch(regex.getvalue(), string, re.DOTALL)
        if not match:
            # The text did not match our pattern
            return None

        result = {name: match[f"_{i}"] for name, i in zip(references, itertools.count())}
        if not ambiguity_check:
            return result

        # Perform an ambiguity check
        # We need an iterator over all the variables in the text, except the last one because `_ambiguity_check` takes a
        # variable and the one after it.
        #
        # [txt, var, txt, var, txt, var, txt, var, txt]
        #      [   ]     [   ]     [   ] <- take this range (every var name except last)
        for i in range(1, len(dissection) - 3, 2):
            lhs_name = dissection[i]
            intermediate = dissection[i + 1]
            rhs_name = dissection[i + 2]  # last var name handled here

            self._ambiguity_check(
                lhs_name,
                result[lhs_name],
                rhs_name,
                result[rhs_name],
                intermediate,
                message="parsing is ambiguous:",
            )

        return result


# pylint: disable=wrong-import-position
from .formats import permissive as _default_engine

# pylint: disable=redefined-builtin
format = _default_engine.format
vformat = _default_engine.vformat
parse = _default_engine.parse
