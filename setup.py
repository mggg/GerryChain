from setuptools import setup
import versioneer

requirements = [
    # package requirements go here
    'pandas',
    "networkx",
    "geopandas",
    "pysal",
    "matplotlib",
    "psutil"
]

setup(
    name='RunDMCMC',
    description="Short description",
    author="Metric Geometry and Gerrymandering Group",
    author_email='gerrymandr@gmail.com',
    url='https://github.com/gerrymandr/RunDMCMC',
    packages=['rundmcmc'],
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    entry_points={
        'console_scripts': [
            'rundmcmc=rundmcmc.__main__:main'
        ]
    },
    install_requires=requirements,
    keywords='RunDMCMC',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ]
)
