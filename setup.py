#! /usr/bin/env python3

import os
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))


with open(os.path.join(here, "pycmds", "VERSION")) as version_file:
    version = version_file.read().strip()


with open("README.md") as readme_file:
    readme = readme_file.read()


extra_files = {"pycmds": ["VERSION"]}

setup(
    name="pycmds",
    packages=find_packages(exclude=("tests", "tests.*")),
    package_data=extra_files,
    python_requires=">=3.7",
    install_requires=["yaqc", "WrightTools"],
    extras_require={"dev": ["black", "pre-commit", "pydocstyle"]},
    version=version,
    description="generic yaq client",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="yaq Developers",
    license="LGPL v3",
    url="https://yaq.fyi",
    project_urls={
        "Source": "https://github.com/wright-group/PyCMDS",
        "Issue Tracker": "https://github.com/wright-group/PyCMDS/issues",
    },
    entry_points={"console_scripts": {"pycmds=pycmds.__main__:main"}},
    keywords="spectroscopy science multidimensional hardware",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering",
    ],
)
