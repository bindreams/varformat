#!/usr/bin/env python3
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
"""Create a python package for the current repository, as if by calling `python -m build`.

Additional work performed by this script consists of determining the binary distribution's listed version. The rules are
described below.

Assuming the version listed in `pyproject.toml` is `1.2.3`:
1. If git HEAD is tagged `v1.2.3`, the distribution is tagged `v1.2.3`.
2. Otherwise, if a git tag `v1.2.3` points to a commit either that is either a child or a parent of HEAD, or does not
   exist at all, the distribution is tagged `v1.2.3.dev0+{short git hash}` (a development release).
3. Otherwise, if that tag exists and points to an unrelated commit, the script aborts with an error.

Assuming the version in `pyproject.toml` follows semantic versioning rules (core version only, no suffixes like
`-alpha`), the script will always produce a distribution with a version specifier compliant with PYPA's guidelines.

See PYPA guidelines for versions: https://packaging.python.org/en/latest/specifications/version-specifiers/
See semantic version specifiers: https://semver.org/
"""

import sys
import tomllib
import re
from pathlib import Path
import shutil
import subprocess as sp

import tomli_w
from git import Repo

re_semver_core = r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"


def parse_version(version_str):
    match = re.match(re_semver_core, version_str)
    if not match:
        raise ValueError(f"version {version_str} did not match the semantic version regex")
    return int(match["major"]), int(match["minor"]), int(match["patch"])


def build():
    shutil.rmtree("dist")
    sp.run([sys.executable, "-m", "build"], check=True)


def main():
    repo = Repo()

    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)

    pyproject_version = pyproject["project"]["version"]
    try:
        parse_version(pyproject_version)
    except ValueError:
        print(
            f"Cannot package - version {pyproject_version} from pyproject.toml does not follow semantic "
            "versioning rules. Note that only the version core (e.g. '1.0.0', and not '1.0.0-alpha') is allowed "
            "by this script."
        )
        return 1

    pyproject_version_tag_name = f"v{pyproject_version}"

    head = repo.head.commit

    if pyproject_version_tag_name in repo.tags:
        # There already is a git tag of this version
        tag = repo.tags[pyproject_version_tag_name].commit

        if tag == head:
            # The tag points to current commit
            package_version = pyproject_version
        elif tag in head.iter_parents() or head in tag.iter_parents():
            # Git tag and HEAD are related commits. It does not matter whether git tag is in front or behind, we mark
            # the distribution as a dev release of that version.
            package_version = f"{pyproject_version}.dev0+{head.hexsha[:7]}"
        else:
            # The tag exists but points somewhere unrelated to this commit, refuse to build.
            print(
                f"Cannot determine version for packaging - tag with version {pyproject_version} from "
                "pyproject.toml already exists in an unrelated commit."
            )
            return 1

    else:
        # There is no git tag of this version, so we will mark this packages as a dev release.
        package_version = f"{pyproject_version}.dev0+{head.hexsha[:7]}"

    if package_version != pyproject_version:
        # We need to overwrite the pyproject.toml file for before calling build.
        Path("pyproject.toml").replace("pyproject.toml.orig")
        try:
            temp_project = dict(pyproject)
            temp_project["project"]["version"] = package_version

            with open("pyproject.toml", "wb") as f:
                tomli_w.dump(temp_project, f)

            build()
        finally:
            Path("pyproject.toml.orig").replace("pyproject.toml")
    else:
        build()


if __name__ == "__main__":
    sys.exit(main())
