from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

TESTS_REQUIRE = [
    "bandit",
    "black>=22.1",
    "dash[testing]",
    "flaky",
    "isort",
    "mypy",
    "pylint",
    "pytest-mock",
    "pytest-xdist",
    "selenium>=3.141",
    "types-dataclasses>=0.1.5; python_version<'3.7'",
    "types-pkg-resources",
    "types-pyyaml",
]

# pylint: disable=line-too-long
setup(
    name="webviz-subsurface",
    description="Webviz config plugins for subsurface data",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/equinor/webviz-subsurface",
    author="R&T Equinor",
    packages=find_packages(exclude=["tests"]),
    package_data={
        "webviz_subsurface": [
            "_abbreviations/abbreviation_data/*.json",
            "_assets/css/*.css",
            "_assets/js/*.js",
            "ert_jobs/config_jobs/*",
        ]
    },
    entry_points={
        "webviz_config_plugins": [
            "OneseismicCrossSection = webviz_subsurface.plugins:OneseismicCrossSection",
        ],
        "console_scripts": ["smry2arrow_batch=webviz_subsurface.smry2arrow_batch:main"],
    },
    install_requires=[
        "dash>=2.0.0",
        "dash_bootstrap_components>=0.10.3",
        "dash-daq>=0.5.0",
        "dataclasses>=0.8; python_version<'3.7'",
        "defusedxml>=0.6.0",
        "ecl2df>=0.15.0; sys_platform=='linux'",
        "fmu-ensemble>=1.2.3",
        "fmu-tools>=1.8",
        "geojson>=2.5.0",
        "jsonschema>=3.2.0",
        "opm>=2020.10.1; sys_platform=='linux'",
        "pandas>=1.1.5",
        "pillow>=6.1",
        "pyarrow>=5.0.0",
        "pydeck>=0.6.2",
        "pyscal>=0.7.5",
        "scipy>=1.2",
        "statsmodels>=0.12.1",  # indirect dependency through https://plotly.com/python/linear-fits/
        "webviz-config>=0.3.8",
        "webviz-core-components>=0.5.6",
        "webviz-subsurface-components>=0.4.11",
        "xtgeo>=2.14",
    ],
    extras_require={"tests": TESTS_REQUIRE},
    setup_requires=["setuptools_scm~=3.2"],
    python_requires="~=3.6",
    use_scm_version=True,
    zip_safe=False,
    project_urls={
        "Documentation": "https://equinor.github.io/webviz-subsurface",
        "Download": "https://pypi.org/project/webviz-subsurface/",
        "Source": "https://github.com/equinor/webviz-subsurface",
        "Tracker": "https://github.com/equinor/webviz-subsurface/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Environment :: Web Environment",
        "Framework :: Dash",
        "Framework :: Flask",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)
