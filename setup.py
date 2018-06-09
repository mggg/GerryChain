from setuptools import setup

requirements = [
    # package requirements go here
]

setup(
    name='RunDMCMC',
    version='Monte-Carlo exploration of districting plans',
    description="Short description",
    author="Metric Geometry and Gerrymandering Group",
    author_email='gerrymandr@gmail.com',
    url='https://github.com/gerrymandr/RunDMCMC',
    packages=['rundmcmc'],
    entry_points={
        'console_scripts': [
            'rundmcmc=rundmcmc.cli:cli'
        ]
    },
    install_requires=requirements,
    keywords='RunDMCMC',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ]
)
