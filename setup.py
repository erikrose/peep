import sys

from setuptools import setup, find_packages


setup(
    name='peep',
    version='0.5',
    description='A "pip install" that is cryptographically guaranteed repeatable',
    long_description=open('README.rst').read(),
    author='Erik Rose',
    author_email='grinch@grinchcentral.com',
    license='MIT',
    packages=find_packages(exclude=['ez_setup']),
    entry_points={
        'console_scripts': ['peep = peep:main']
        },
    url='https://github.com/erikrose/peep',
    include_package_data=True,
    install_requires=['pip'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration'
        ],
    keywords=['pip', 'secure', 'repeatable', 'deploy', 'deployment', 'hash']
)
