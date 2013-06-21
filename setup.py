import sys

from setuptools import setup, find_packages


setup(
    name='peep',
    version='0.1',
    description='A "pip install" that is cryptographically guaranteed repeatable',
    long_description=open('README.rst').read(),
    author='Erik Rose',
    author_email='grinch@grinchcentral.com',
    license='MIT',
    packages=find_packages(exclude=['ez_setup']),
    scripts=['bin/peep'],
    url='https://github.com/erikrose/peep',
    include_package_data=True,
    install_requires=['pip'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Build Tools'
        ],
    keywords=['pip', 'secure', 'repeatable', 'deploy', 'deployment', 'hash']
)
