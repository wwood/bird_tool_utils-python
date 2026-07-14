"""Shared logic for generating environment.yml and requirements.txt from a
pixi.toml. Used by aviary, singlem, and any other bird-suite repo."""

from __future__ import annotations
import json
import subprocess
import tomllib
from typing import Any

import yaml

DEFAULT_MIXED_SECTIONS: list[str | list[str]] = [
    "dependencies",
    "host-dependencies",
    ["feature", "main", "dependencies"],
    ["feature", "main", "host-dependencies"],
]


def _read_section(pixi_data: dict, section: str | list[str]) -> set[str]:
    if isinstance(section, list):
        d: Any = pixi_data
        for key in section:
            d = d.get(key, {})
    else:
        d = pixi_data.get(section, {})
    print(f"Found {len(d)} declared packages in section {section}.")
    return {pkg.lower() for pkg in d}


def build_dep_defs(
    *,
    pixi_toml_path: str,
    environment_yml_path: str,
    requirements_txt_path: str,
    conda_to_pip_name: dict[str, str] | None = None,
    project_name: str | None = None,
    environment: str | None = None,
    python_sections: list[str | list[str]] | None = None,
    nonpython_sections: list[str | list[str]] | None = None,
    mixed_sections: list[str | list[str]] | None = None,
) -> None:
    """Generate environment.yml and requirements.txt from a pixi.toml.

    Args:
        pixi_toml_path: Path to the pixi.toml to read.
        environment_yml_path: Output path for environment.yml.
        requirements_txt_path: Output path for requirements.txt.
        conda_to_pip_name: Mapping of conda package names to PyPI names where
            they diverge (e.g. {"bird_tool_utils_python": "bird_tool_utils"}).
        project_name: Conda/PyPI name of the project itself, excluded from
            requirements.txt. If None, reads workspace.name from pixi.toml.
        environment: pixi environment to query for installed versions (e.g.
            "dev"). When set, `pixi list` and `pixi run pip list` run against
            this environment via --environment. Membership of the output is
            still controlled by the *_sections whitelist, so dev-only tools do
            not leak in — this only affects which env supplies the version
            pins. If None, pixi's default environment is used.
        python_sections: pixi.toml sections containing only Python deps.
            Every package here must appear in `pip list` (or conda_to_pip_name).
        nonpython_sections: pixi.toml sections containing only non-Python deps.
            These are included in environment.yml but not requirements.txt.
        mixed_sections: pixi.toml sections containing a mix of Python and
            non-Python deps. Defaults to DEFAULT_MIXED_SECTIONS.
    """
    conda_to_pip_name = conda_to_pip_name or {}
    python_sections = python_sections or []
    nonpython_sections = nonpython_sections or []
    mixed_sections = mixed_sections if mixed_sections is not None else DEFAULT_MIXED_SECTIONS

    with open(pixi_toml_path, "rb") as f:
        pixi_data = tomllib.load(f)

    env_flag = ["--environment", environment] if environment else []

    result = subprocess.run(
        ["pixi", "list", *env_flag, "--json"],
        capture_output=True, text=True, check=True,
    )
    pixi_list = {
        pkg["name"].lower(): pkg["version"]
        for pkg in json.loads(result.stdout)
        if not pkg.get("is_editable")
    }
    print(f"Found {len(pixi_list)} pixi packages.")

    result = subprocess.run(
        ["pixi", "run", *env_flag, "pip", "list", "--format", "json"],
        capture_output=True, text=True, check=True,
    )
    pip_list = sorted(json.loads(result.stdout), key=lambda x: x["name"].lower())

    python_conda = (
        set().union(*(_read_section(pixi_data, s) for s in python_sections))
        if python_sections else set()
    )
    nonpython_conda = (
        set().union(*(_read_section(pixi_data, s) for s in nonpython_sections))
        if nonpython_sections else set()
    )
    mixed_conda = set().union(*(_read_section(pixi_data, s) for s in mixed_sections))
    declared_conda = python_conda | nonpython_conda | mixed_conda

    # Catch stale entries in conda_to_pip_name early
    for conda_name in conda_to_pip_name:
        if conda_name not in declared_conda:
            raise ValueError(
                f"conda_to_pip_name has stale entry: {conda_name!r} is not declared in pixi.toml."
            )

    # Every python-section dep must resolve to a pip package
    pip_names = {pkg["name"].lower() for pkg in pip_list}
    required_pip_names: set[str] = set()
    for conda_name in python_conda:
        if conda_name == "python":
            continue
        pip_name = conda_to_pip_name.get(conda_name, conda_name).lower()
        if pip_name not in pip_names:
            raise ValueError(
                f"Conda package {conda_name!r} (python section) not in `pip list` as {pip_name!r}. "
                f"Add a conda_to_pip_name entry if the PyPI name differs."
            )
        required_pip_names.add(pip_name)

    mixed_pip_names = {conda_to_pip_name.get(p, p).lower() for p in mixed_conda}
    declared_pip = required_pip_names | mixed_pip_names

    if project_name is None:
        project_name = pixi_data.get("workspace", {}).get("name", "").lower()
    if not project_name:
        raise ValueError("project_name not provided and workspace.name not found in pixi.toml.")
    print(f"Excluding project from output files: {project_name}")

    # Write environment.yml
    conda_deps = sorted(
        f"{pkg}={pixi_list[pkg]}" for pkg in declared_conda if pkg in pixi_list
    )
    env_data = {"channels": ["conda-forge", "bioconda"], "dependencies": conda_deps}
    with open(environment_yml_path, "w") as f:
        f.write("# This file was autogenerated by build_dep_defs_from_pixi.py - do not change manually.\n")
        yaml.dump(env_data, f, default_flow_style=False)
    print(f"environment.yml written with {len(conda_deps)} dependencies.")

    # Write requirements.txt
    pip_count = 0
    with open(requirements_txt_path, "w") as f:
        f.write("# This file was autogenerated by build_dep_defs_from_pixi.py - do not change manually.\n")
        for package in pip_list:
            if package["name"].lower() not in declared_pip:
                continue
            if package["name"].lower() == project_name:
                continue
            pip_count += 1
            if package["version"] == "0.0.0":
                f.write(f"{package['name']}\n")
            else:
                f.write(f"{package['name']}=={package['version']}\n")
    print(f"requirements.txt written with {pip_count} dependencies.")
