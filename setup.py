import sys

# Prevent spurious errors during `python setup.py test`, a la
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html:
try:
    import multiprocessing  # noqa
except ImportError:
    pass

from setuptools import setup


setup(
    name='peep',
    version='3.1.2',
    description='A "pip install" that is cryptographically guaranteed repeatable',
    long_description=open('README.rst').read(),
    author='Erik Rose',
    author_email='grinch@grinchcentral.com',
    license='MIT',
    py_modules=['peep'],
    entry_points={
        'console_scripts': ['peep = peep:main',
                            'peep-%s.%s = peep:main' % sys.version_info[:2]]
    },
    url='https://github.com/erikrose/peep',
    include_package_data=True,
    # No dependencies are declared for peep, even though it requires pip.
    # install_requires=['pip>=0.6.2'],
    tests_require=['nose>=1.3.0,<2.0'],
    test_suite='nose.collector',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration'
    ],
    keywords=['pip', 'secure', 'repeatable', 'deploy', 'deployment', 'hash',
              'install', 'installer']
)
