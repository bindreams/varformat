# Copyright 2023 Andrey Zhukov
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
import re
import io
from typing import Iterable, TypeAlias, Any

Location: TypeAlias = tuple[int, int]
References: TypeAlias = dict[str, list[Location]]
Replacements: TypeAlias = list[Location, str, Any]

class AmbiguityError(ValueError):
    def __init__(self, message, possibilities: Iterable[dict]):
        compiled_message = io.StringIO()
        compiled_message.write(message)

        prefix = "\n  could be: "
        for possibility in possibilities:
            compiled_message.write(prefix)
            compiled_message.write(str(possibility))
            prefix = "\n        or: "

        super().__init__(compiled_message.getvalue())


re_variable = re.compile(r"\${(\w+)}")
def _references(fmtstring: str) -> References:
    """Produce a map {var_name: [location, ...]} for a format string."""
    result = {}

    for reference in re.finditer(re_variable, fmtstring):
        variable = reference[1]
        locations = result.get(variable, [])
        locations.append((reference.start(), reference.end()))
        result[variable] = locations

    return result


def _replacements(references: References, args: dict[str, Any], *, partial_ok, extra_ok):
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


def format(fmtstring: str, /, **kwargs):
    return vformat(fmtstring, kwargs)

def _ambiguity_check(lhs_name, lhs_text, rhs_name, rhs_text, intermediate, message):
    """Performs an ambiguity check during format for a pair of sequential variables.

    :param lhs_name: name of the left side variable
    :param lhs_text: text of the left side variable
    :param rhs_name: name of the right side variable
    :param rhs_text: text of the right side variable
    :param intermediate: unformatted text between variables
    """
    i = rhs_text.find(intermediate)
    if i != -1:
        raise AmbiguityError(message, [
            {lhs_name: lhs_text,                               rhs_name: rhs_text},
            {lhs_name: lhs_text + intermediate + rhs_text[:i], rhs_name: rhs_text[i+len(intermediate):]}
        ])

    i = lhs_text.find(intermediate)
    if i != -1:
        raise AmbiguityError(message, [
            {lhs_name: lhs_text,     rhs_name: rhs_text},
            {lhs_name: lhs_text[:i], rhs_name: lhs_text[i+len(intermediate):] + intermediate + rhs_text}
        ])


def _format_iter(fmtstring: str, replacements: list[tuple[tuple[int, int], str, str]]):
    """Yields parts of the output string.

    Yield values alternate between `str` (non-formatted text, even if empty) and tuple[str, str] (variable name and the
    text replacement). Starts with `str` and ends with `str`.

    If the format string is empty, will generate a single empty `str`.
    """
    prev_end = 0

    for location, name, replacement_val in replacements:
        yield fmtstring[prev_end:location[0]]
        yield (name, str(replacement_val))

        prev_end = location[1]

    yield fmtstring[prev_end:]


def vformat(fmtstring: str, /, args: dict, *, partial_ok=False, extra_ok=True, ambiguity_check=False):
    references = _references(fmtstring)
    replacements = _replacements(references, args, partial_ok=partial_ok, extra_ok=extra_ok)

    result = io.StringIO()
    iterator = iter(_format_iter(fmtstring, replacements))

    name_last = None
    replacement_last = None
    try:
        while True:
            intermediate = next(iterator)
            result.write(intermediate)

            name, replacement = next(iterator)
            result.write(replacement)

            if ambiguity_check and name_last is not None:
                _ambiguity_check(
                    name_last, replacement_last, name, replacement, intermediate,
                    message="refusing to format because parsing would be ambiguous:"
                )

            name_last = name
            replacement_last = replacement
    except StopIteration:
        pass

    return result.getvalue()


def parse(fmtstring: str, /, string: str, *, ambiguity_check=True):
    references = _references(fmtstring)
    args = {}

    for name in references:
        args[name] = f"(?P<_{name}>.*)"

    replacements = _replacements(references, args, partial_ok=False, extra_ok=False)
    dissection = []  # a list of [unformatted text, variable name, unformatted text, ...]
    regex = io.StringIO()  # A regular expressions with named capture groups in place of dollar variables
    iterator = iter(_format_iter(fmtstring, replacements))
    try:
        while True:
            intermediate = next(iterator)
            dissection.append(intermediate)
            regex.write(re.escape(intermediate))

            name, replacement = next(iterator)
            dissection.append(name)
            regex.write(replacement)
    except StopIteration:
        pass

    match = re.fullmatch(regex.getvalue(), string, re.DOTALL)
    if not match:
        return None

    result = {name: match[f"_{name}"] for name in references}
    if not ambiguity_check:
        return result

    # [txt, var, txt, var, txt, var, txt, var, txt]
    #      [   ]     [   ]     [   ] <- take this range (every var name except last)
    for i in range(1, len(dissection)-3, 2):
        lhs_name = dissection[i]
        intermediate = dissection[i+1]
        rhs_name = dissection[i+2]  # last var name handled here

        _ambiguity_check(
            lhs_name, result[lhs_name], rhs_name, result[rhs_name], intermediate,
            message="parsing is ambiguous:"
        )

    return result
