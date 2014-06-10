import sys

from setuptools import setup, find_packages


setup(
    name='peep',
    version='1.2',
    description='A "pip install" that is cryptographically guaranteed repeatable',
    long_description=open('README.rst').read(),
    author='Erik Rose',
    author_email='grinch@grinchcentral.com',
    license='MIT',
    py_modules=['peep'],
    entry_points={
        'console_scripts': ['peep = peep:main']
        },
    url='https://github.com/erikrose/peep',
    include_package_data=True,
    # No dependencies are declared for peep, even though it requires pip.
    # install_requires=['pip>=0.6.2'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration'
        ],
    keywords=['pip', 'secure', 'repeatable', 'deploy', 'deployment', 'hash']
)
