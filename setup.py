# -*- coding: utf-8 -*-
import ast
from pathlib import Path

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in posawesome/__init__.py
version_file = Path("posawesome/__init__.py").read_text()
version = None
for node in ast.parse(version_file).body:
    if not isinstance(node, ast.Assign):
        continue
    if any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
        version = ast.literal_eval(node.value)
        break

if version is None:
    raise RuntimeError("Unable to find __version__ in posawesome/__init__.py")

setup(
    name="posawesome",
    version=version,
    description="POS Awesome",
    author="Yousef Restom",
    author_email="youssef@totrox.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
