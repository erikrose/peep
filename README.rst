.. image:: https://api.travis-ci.org/erikrose/peep.svg

====
Peep
====

Historically, deploying Python projects has been a pain in the neck for the
security-conscious. First, PyPI lets authors change the contents of their
packages without revving their version numbers. Second, any future compromise
of PyPI or its caching CDN means you could get a package that's different from
the one you signed up for. If you wanted to guarantee known-good dependencies
for your deployment, you had to either run a local PyPI mirror--manually
uploading packages as you vetted them--or else check everything into a vendor
library, necessitating a lot of fooling around with your VCS (or maintaining
custom tooling) to do upgrades.

Peep fixes all that.

Vet your packages, put hashes of the PyPI-sourced tarballs into
``requirements.txt``, use ``peep install`` instead of ``pip install``, and let
the crypto do the rest. If a downloaded package doesn't match the hash,
``peep`` will freak out, and installation will go no further. No servers to
maintain, no enormous vendor libs to wrestle. Just ``requirements.txt`` with
some funny-looking comments and peace of mind.


Switching to Peep
=================

0. Install ``peep``::

    pip install peep
1. Use ``peep`` to install your project once::

        cd yourproject
        peep install -r requirements.txt

   You'll get output like this::

    <a bunch of pip output>

    The following packages had no hashes specified in the requirements file,
    which leaves them open to tampering. Vet these packages to your
    satisfaction, then add these "sha256" lines like so:

    # sha256: L9XU_-gfdi3So-WEctaQoNu6N2Z3ZQYAOu4-16qor-8
    Flask==0.9

    # sha256: YhddA1kUpMLVODNbhIgHfQn88vioPHLwayTyqwOJEgY
    futures==2.1.3

    # sha256: qF4YU3XbdcEJ-Z7N49VUFfA15waKgiUs9PFsZnrDj0k
    Jinja2==2.6

    # sha256: u_8C3DCeUoRt2WPSlIOnKV_MAhYkc40zNZxDlxCA-as
    Pygments==1.4

    # sha256: A1gwhyCNozcxug18_9RjJTmJQa1rctOt-AnP7_yR0PM
    https://github.com/jsocol/commonware/archive/b5544185b2d24adc1eb512735990752400ce9cbd.zip#egg=commonware

    -------------------------------
    Not proceeding to installation.
2. Vet the packages coming off PyPI in whatever way you typically do.
3. Add the recommended hash lines to your ``requirements.txt``, each one
   directly above the requirement it applies to. (The hashes are of the
   original, compressed tarballs from PyPI.)
4. In the future, always use ``peep install`` to install your requirements. You
   are now cryptographically safe!

.. warning::

    Be careful not to nullify all your work when you install your actual
    project. If you use ``python setup.py install``, setuptools will happily go
    out and download, unchecked, any requirements you missed in
    ``requirements.txt`` (and it's easy to miss some as your project evolves).
    One way to be safe is to pack up your project and then install that using
    pip and ``--no-deps``::

        python setup.py sdist
        pip install --no-deps dist/yourproject-1.0.tar.gz


Security Guarantees
===================

1. Peep guarantees repeatability.

   If you ``peep install`` package x version y, every subsequent install of package
   x version y will be the same as the original, or Peep will complain.

2. Peep does not vet your packages.

   Peep is not a substitute for vetting your packages. If you don't vet them,
   then they are not vetted.

3. Peep does not alleviate trust problems with authors or package indexes.

   All peep does is guarantee that subsequent downloads of package x version y
   are the same as the first one you did. It doesn't guarantee the author of
   that package is trustworthy. It doesn't guarantee that the author of that
   package released that package. It doesn't guarantee that the package index
   is trustworthy.


The Fearsome Warning
====================

If, during installation, a hash doesn't match, ``peep`` will say something like
this::

    THE FOLLOWING PACKAGES DIDN'T MATCH THE HASHES SPECIFIED IN THE
    REQUIREMENTS FILE. If you have updated the package versions, update the
    hashes. If not, freak out, because someone has tampered with the packages.

        requests: expected FWvz7Ce6nsfgz4--AoCHGAmdIY3kA-tkpxTXO6GimrE
                       got YhddA1kUpMLVODNbhIgHfQn88vioPHLwayTyqwOJEgY

It will then exit with a status of 1. Freak out appropriately.


Other Niceties
==============

* ``peep`` implicitly turns on pip's ``--no-deps`` option so unverified
  dependencies of your requirements can't sneak through.
* All non-install commands just fall through to pip, so you can use ``peep``
  all the time if you want. This comes in handy for existing scripts that have
  a big ``$PIP=/path/to/pip`` at the top.
* ``peep``-compatible requirements files remain entirely usable with ``pip``,
  because the hashes are just comments, after all.
* Have a manually downloaded package you've vetted? Run ``peep hash`` on its
  tarball (the original, from PyPI--be sure to keep it around) to get its hash
  line::

    % peep hash nose-1.3.0.tar.gz
    # sha256: TmPMMyXedc-Y_61AvnL6aXU96CRpUXMXj3TANP5PUmA
* If a package is already present--which might be the case if you're installing
  into a non-empty virtualenv--``peep`` doesn't bother downloading or building it
  again. It assumes you installed it with ``peep`` in a previous invocation and
  thus trusts it. Re-using a virtualenv during deployment can really speed
  things up, but it does leave open the question of how to remove dependencies
  which are no longer needed.


Embedding
=========

Peep was designed for unsupervised continuous deployment scenarios. In such
scenarios, manual ahead-of-time prepartion on the deployment machine is a
liability: one more thing to go wrong. To relieve you of having to install (and
upgrade) ``peep`` by hand on your server or build box, we've made ``peep``
embeddable. You can copy the ``peep.py`` file directly into your project's
source tree and call it from there in your deployment script. This also gives
you an obvious starting point for your chain of trust: however you trust your
source code is how you trust your copy of ``peep``, and ``peep`` verifies
everything else via hashes. (Equivalent would be if your OS provided peep as a
package--presumably you trust your OS packages already--but this is not yet
common.)


Troubleshooting
===============

Upgrading wheels
----------------

If you're reusing a virtualenv, then you should avoid wheels until a version
of pip that upgrades wheels properly is out. Otherwise, the old version of a
package will not be entirely removed before the new one is installed. See
https://github.com/pypa/pip/issues/1825 for more details.

If you're using pip 1.4, don't pass the ``--use-wheel`` argument.

If you're using pip 1.5, pass the ``--no-use-wheel`` argument.

Multiple Hashes: Architecture-Specific Packages and Old Versions of PyPI
------------------------------------------------------------------------

Are you suddenly getting the Fearsome Warning? Maybe you're really in trouble,
but maybe something more innocuous is happening.

If your packages install from wheels or other potentially architecture-specific
sources, their hashes will obviously differ across platforms. If you deploy on
more than one, you'll need more than one hash.

Also, some packages offer downloads in multiple formats: for example, zips and
tarballs, or zips and wheels. Which version gets downloaded can vary based on
your version of pip, meaning some packages may effectively have more than one
valid hash.

To support these scenarios, you can stack up multiple known-good hashes above a
requirement, as long as they are within a contiguous block of commented lines::

    # Tarball:
    # sha256: lvpN706AIAvoJ8P1EUfdez-ohzuSB-MyXUe6Rb8ppcE
    #
    # And the zip file:
    # sha256: 6QTt-5DahBKcBiUs06BfkLTuvBu1uF7pblb_bPaUONU
    mock==0.8.0

If you don't want to wait until you're bitten by this surprise, use the ``peep
hash`` command to find hashes of each equivalent archive for a package. I like
to vet one of them (say, the tarball), then download the other and use a file
comparison tool to verify that they have identical contents. Then I run ``peep
hash`` over both original archives, like so, and add the result to my
``requirements.txt``::

    % peep hash mock-0.8.0.tar.gz mock-0.8.0.zip
    # sha256: lvpN706AIAvoJ8P1EUfdez-ohzuSB-MyXUe6Rb8ppcE
    # sha256: 6QTt-5DahBKcBiUs06BfkLTuvBu1uF7pblb_bPaUONU


Version History
===============

2.3
  * Copy the operative portion of the MIT license into peep.py so embedding it
    doesn't break the license.
  * Fix flake8 linter warnings.
  * Make peep compatible with pip v6.1.0+.
  * Add tests against pip 6.0.8, 6.1.0, and 6.1.1 to the tox config.
  * Run full set of tox tests on Travis.

2.2
  * Add progress indication while downloading. Used with pip 6.0 and above, we
    show a nice progress bar. Before that, we just mention the packages as we
    download them.
  * Remove extra skipped lines from the output.
  * Add tests against pip 6.0.7 to the tox config.

2.1.2
  * Get rid of repetition of explanatory messages at the end of a run when one
    applies to multiple packages.

2.1.1
  * Fix bug in which peep would not upgrade a package expressed in terms of a
    GitHub-dwelling zip file if its version had not changed.
  * Add tests against pip 6.0.4, 6.0.5, and 6.0.6 to the tox config.

2.1
  * Support pip 6.x.
  * Make error reporting friendly, emitting a bug reporting URL and
    environment info along with the traceback.

2.0
  * Fix major security hole in which a package's setup.py would be executed
    after download, regardless of whether the package's archive matched a hash.
    Specifically, stop relying on pip for downloading packages, as it likes to
    run setup.py to extract metadata. Implement our own downloading using
    what's available everywhere: urllib2. As a result, HTTP proxies,
    basic auth, and ``--download-cache`` are unsupported at the moment.
  * Refactor significantly for comprehensibility.
  * Drastically improve test coverage.
  * Note that HTTPS certs are no longer checked. This shouldn't matter, given
    our hash checks.

1.4
  * Allow partial-line comments.
  * Add the beginnings of a test suite.
  * Treat package names in requirements files as case-insensitive, like pip.

1.3
  * Pass through most args to the invocation of ``pip install`` that actually
    installs the downloaded archive. This means you can use things like
    ``--install-options`` fruitfully.
  * Add Python 3.4 support by correcting an import.
  * Install a second peep script named after the active Python version, e.g.
    peep-2.7. This is a convenience for those using multiple versions of
    Python and not using virtualenvs.

1.2
  * Support GitHub-style tarballs (that is, ones whose filenames don't contain
    the distro name or version and whose version numbers aren't reliable) in
    requirements files. (Will Kahn-Greene)
  * Warn when a URL-based requirement lacks ``#egg=``. (Chris Adams)

1.1
  * Support Python 3. (Keryn Knight)

1.0.2
  * Add support for .tar.bz2 archives. (Paul McLanahan)

1.0.1
  * Fix error (which failed safe) installing packages whose distro names
    contain underscores. (Chris Ladd)

1.0
  * Add wheel support. Peep will now work fine when pip decides to download a
    wheel file. (Paul McLanahan)

0.9.1
  * Don't crash when trying to report a missing hash on a package that's
    already installed.

0.9
  * Put the operative parts of peep into a single module rather than a package,
    and make it directly executable. (Brian Warner)

0.8
  * Support installing into non-empty virtualenvs, for speed. We do this by
    trusting any already-installed package which satisfies a requirement. This
    means you no longer have to rebuild ``lxml``, for instance, each time you
    deploy.
  * Wrap text output to 80 columns for nicer word wrap.

0.7
  Make some practical tweaks for projects which bootstrap their trust chains by
  checking a tarball of peep into their source trees.

  * Start supporting versions of pip back to 0.6.2 (released in January 2010).
    This way, you can deploy trustworthily on old versions of RHEL just by
    checking a tarball of peep into your source tree and pip-installing it; you
    don't have to check in pip itself or go to the bother of unpacking the peep
    tarball and running ``python setup.py install`` from your deploy script.
  * Remove the explicit dependency on pip. This is so a blithe call to
    ``pip install peep.tar.gz`` without ``--no-deps`` doesn't go out and pull
    an untrusted package from PyPI. Instead, we scream at runtime if pip is
    absent or too old. Fail safe.

0.6
  * Add ``peep hash`` subcommand.
  * Require pip>=1.2, as lower versions have a bug that causes a crash on
    ``peep install``.

0.5
  * Allow multiple acceptable hashes for a package. This works around PyPI's
    non-stable handling of packages like mock, which provide equivalent
    zips and tarballs:
    https://bitbucket.org/pypa/pypi/issue/64/order-of-archives-on-index-page-is-not.

0.4
  * Rework how peep downloads files and determines versions so we can tolerate
    PEP-386-noncompliant package version numbers. This amounted to a minor
    rewrite.
  * Remove indentation from hash output so you don't have to dedent it after
    pasting it into ``requirements.txt``.

0.3
  * Support Windows and other non-Unix OSes.
  * The hash output now includes the actual version numbers of packages, so you
    can just paste it straight into your ``requirements.txt``.

0.2.1
  * Add a shebang line so you can actually run ``peep`` after doing ``pip
    install peep``. Sorry, folks, I was doing ``setup.py develop`` on my own
    box.

0.2
  * Fix repeated-logging bug.
  * Fix spurious error message about not having any requirements files.
  * Pass pip's exit code through to the outside for calls to non-``install``
    subcommands.
  * Improve spacing in the final output.

0.1
  * Proof of concept. Does all the crypto stuff. Should be secure. Some rough
    edges in the UI.
