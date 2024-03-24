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

Additional work performed by this script consists of determining the binady distribution's listed version. The rules are
described below.

Assuming the version listed in `pyproject.toml` is `1.2.3`:
1. If the current git commit is tagged `v1.2.3`, the distribution is tagged `v1.2.3`.
2. Otherwise, if a git tag `v1.2.3` does not exist, the distribution is tagged `v1.2.3a0.dev+{short git hash}` (an
   alpha development pre-release).
3. Otherwise, if that tag exists and points to an ancestor of the current commit, the distribution is tagged
   `v1.2.3r0.dev+{short git hash}` (a development post-release).
4. Otherwise, if that tag exists and points to an unrelated commit, the script aborts with an error.

Keep in mind that the version tag that this script produces may be (and currently is) further normalized by the build
tool itself.

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
        project = tomllib.load(f)

    pyprojecttoml_version = project["project"]["version"]
    try:
        parse_version(pyprojecttoml_version)
    except ValueError:
        print(
            f"Cannot package - version {pyprojecttoml_version} from pyproject.toml does not follow semantic "
            "versioning rules. Note that only the version core (e.g. '1.0.0', and not '1.0.0-alpha') is allowed "
            "by this script."
        )
        return 1

    pyprojecttoml_version_tag_name = f"v{pyprojecttoml_version}"

    head = repo.head.commit

    if pyprojecttoml_version_tag_name in repo.tags:
        # There already is a git tag of this version
        tag = repo.tags[pyprojecttoml_version_tag_name].commit

        if tag == head:
            # The tag points to current commit
            package_version = pyprojecttoml_version
        elif tag in head.iter_parents():
            # The tag points to a parent of current commit, we will increment this version's major number by 1 and add
            # an 'alpha' tag with git hash.
            parsed = parse_version(pyprojecttoml_version)
            package_version = f"{pyprojecttoml_version}r0.dev+{head.hexsha[:7]}"
        else:
            # The tag exists but points somewhere unrelated to this commit, refuse to build.
            print(
                f"Cannot determine version for packaging - tag with version {pyprojecttoml_version} from "
                "pyproject.toml already exists in an unrelated commit."
            )
            return 1

    else:
        # There is no released tag of this version, we will use this version and add an 'alpha' tag with git hash.
        package_version = f"{pyprojecttoml_version}a0.dev+{head.hexsha[:7]}"

    if package_version != pyprojecttoml_version:
        # We need to overwrite the pyproject.toml file for before calling build.
        Path("pyproject.toml").replace("pyproject.toml.orig")
        try:
            temp_project = dict(project)
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
