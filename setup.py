from setuptools import find_packages, setup

import versioneer

with open("./README.rst") as f:
    long_description = f.read()

requirements = [
    # package requirements go here
    "pandas",
    "scipy",
    "networkx",
    "matplotlib",
]

setup(
    name="gerrychain",
    description="Use Markov chain Monte Carlo to analyze districting plans and gerrymanders",
    author="Metric Geometry and Gerrymandering Group",
    author_email="engineering@mggg.org",
    maintainer="Metric Geometry and Gerrymandering Group",
    maintainer_email="engineering@mggg.org",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/mggg/GerryChain",
    packages=find_packages(exclude=("tests",)),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    install_requires=requirements,
    keywords="GerryChain",
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
    extras_require={
        'geo': ["shapely>=2.0.1", "geopandas>=0.12.2"]
    }
)
