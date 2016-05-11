.. image:: https://travis-ci.org/erikrose/peep.svg?branch=master
    :target: https://travis-ci.org/erikrose/peep

.. note::

    Peep is deprecated, as we have `merged its functionality into pip 8
    <https://pip.readthedocs.org/en/stable/reference/pip_install/#hash-checking
    -mode>`_. This brings myriad improvements, including support for caching,
    detection of omitted dependencies, and better handling of errors and corner
    cases. To switch to pip 8's hash-checking without hitting any race
    conditions...

    1. Upgrade to peep 3.0 (which exists mainly as a stopgap to support
       race-free upgrades like this).
    2. Upgrade to pip 8.
    3. Atomically, switch the format of your requirements files using ``peep
       port`` (described below), and start calling pip instead of peep.
    4. Delete peep from your project.

    Thank you for using peep! Your early support helped establish hash
    verification as a feature worth uplifting, and now the package ecosystem is
    safer for everyone.

    Here are some `more detailed upgrade instructions
    <https://github.com/erikrose/peep/wiki/UpgradeToPip8>`_ in case you need
    them.

====
Peep
====

Deploying Python projects has long been a source of frustration for the
security-conscious: a compromise of PyPI or its third-party CDN could get
you a package different from the one you signed up for. To guarantee
known-good dependencies for your deployments, you had to run a local package
index, manually uploading packages as you vetted them, maintaining a set of
ACLs for that server, and trying to somehow keep an audit trail of who did
what. Alternatively, you could check everything into a vendor library, but that
meant a lot of fooling around with your VCS (or maintaining custom tooling) to
do upgrades.

Peep fixes all that.

Vet your packages, and put hashes of the PyPI-sourced tarballs into
``requirements.txt``, like this::

    # sha256: L9XU_-gfdi3So-WEctaQoNu6N2Z3ZQYAOu4-16qor-8
    Flask==0.9

    # sha256: qF4YU3XbdcEJ-Z7N49VUFfA15waKgiUs9PFsZnrDj0k
    Jinja2==2.6

Then, use ``peep install`` instead of ``pip install``, and let the crypto do
the rest. If a downloaded package doesn't match the expected hash, Peep will
freak out, and installation will go no further.

There are no servers to maintain, no enormous vendor libs to wrestle, and no
need to trust a package author's key management practices. With the addition
of a few hashes to your requirements file, you can know that your chain of
trust is safely rooted in your own source tree.


Switching to Peep
=================

1. Install Peep::

    pip install peep

   (Or, better, embed ``peep.py`` into your codebase as described in the
   Embedding section below. That eliminates having to trust an unauthenticated
   PyPI download, assuming you manually vet ``peep.py`` itself the first time.)
2. Use Peep to install your project once::

        cd yourproject
        peep install -r requirements.txt

   You'll get output like this::

    <a bunch of pip output>

    The following packages had no hashes specified in the requirements file,
    which leaves them open to tampering. Vet these packages to your
    satisfaction, then add these "sha256" lines like so:

    # sha256: L9XU_-gfdi3So-WEctaQoNu6N2Z3ZQYAOu4-16qor-8
    Flask==0.9

    # sha256: qF4YU3XbdcEJ-Z7N49VUFfA15waKgiUs9PFsZnrDj0k
    Jinja2==2.6

    # sha256: u_8C3DCeUoRt2WPSlIOnKV_MAhYkc40zNZxDlxCA-as
    Pygments==1.4

    # sha256: A1gwhyCNozcxug18_9RjJTmJQa1rctOt-AnP7_yR0PM
    https://github.com/jsocol/commonware/archive/b5544185b2d24adc1eb512735990752400ce9cbd.zip#egg=commonware

    -------------------------------
    Not proceeding to installation.
3. Vet the packages coming off PyPI in whatever way you typically do. For
   instance, read them, or compare them with known-good local copies.
4. Add the recommended hash lines to your ``requirements.txt``, each one
   directly above the requirement it applies to. (The hashes are of the
   original, compressed tarballs from PyPI.)
5. In the future, always use ``peep install`` to install your requirements. You
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


The Fearsome Warning
====================

If, during installation, a hash doesn't match, Peep will say something like
this::

    THE FOLLOWING PACKAGES DIDN'T MATCH THE HASHES SPECIFIED IN THE
    REQUIREMENTS FILE. If you have updated the package versions, update the
    hashes. If not, freak out, because someone has tampered with the packages.

        requests: expected FWvz7Ce6nsfgz4--AoCHGAmdIY3kA-tkpxTXO6GimrE
                       got YhddA1kUpMLVODNbhIgHfQn88vioPHLwayTyqwOJEgY

It will then exit with a status of 1. Freak out appropriately.


Other Features
==============

* Peep implicitly turns on pip's ``--no-deps`` option so unverified
  dependencies of your requirements can't sneak through.
* All non-install commands just fall through to pip, so you can use Peep
  all the time if you want. This comes in handy for existing scripts that have
  a big ``$PIP=/path/to/pip`` at the top.
* Peep-compatible requirements files remain entirely usable with ``pip``,
  because the hashes are just comments, after all.
* Have a manually downloaded package you've vetted? Run ``peep hash`` on its
  tarball (the original, from PyPI--be sure to keep it around) to get its hash
  line::

    % peep hash nose-1.3.0.tar.gz
    # sha256: TmPMMyXedc-Y_61AvnL6aXU96CRpUXMXj3TANP5PUmA
* If a package is already present--which might be the case if you're installing
  into a non-empty virtualenv--Peep doesn't bother downloading or building it
  again. It assumes you installed it with Peep in a previous invocation and
  thus trusts it. The only exception to this is for URL-specified requirements where the
  URL contains a SHA-like filename (eg https://github.com/foo/bar/archive/<SHA>.zip),
  since the package version number is typically not incremented for every commit, so
  Peep cannot be sure the contents have not changed. 
  Note: Re-using a virtualenv during deployment can really speed things up, but you will
  need to manually remove dependencies that are no longer in the requirements file.
* ``peep port`` converts a peep-savvy requirements file to one compatible with
  `pip 8's new hashing functionality
  <https://pip.pypa.io/en/latest/reference/pip_install/#hash-checking-mode>`_::

    % peep port requirements.txt
    certifi==2015.04.28 \
        --hash=sha256:268fa00c27de756d71663dd61f73a4a8d8727569bb1b474b2ce6020553826872 \
        --hash=sha256:99785e6cf715cdcde59dee05a676e99f04835a71e7ced201ca317401c322ba96
    click==4.0 --hash=sha256:9ab1d313f99b209f8f71a629f36833030c8d7c72282cf7756834baf567dca662

  Note that comments and URLs don't make it through, but the hard part—hash
  format conversion—is taken care of for you.


Embedding
=========

Peep was designed for unsupervised continuous deployment scenarios. In such
scenarios, manual ahead-of-time preparation on the deployment machine is a
liability: one more thing to go wrong. To relieve you of having to install (and
upgrade) Peep by hand on your server or build box, we've made Peep
embeddable. You can copy the ``peep.py`` file directly into your project's
source tree and call it from there in your deployment script. This also gives
you an obvious starting point for your chain of trust: however you trust your
source code is how you trust your copy of Peep, and Peep verifies
everything else via hashes. (Equivalent would be if your OS provided Peep as a
package--presumably you trust your OS packages already--but this is not yet
common.)


Security and Insecurity
=======================

Here's what you get for free with Peep--and what you don't.

**You get repeatability.** If you ``peep install`` package ``Foo==1.2.3``,
every subsequent install of ``Foo==1.2.3`` will be the same as the original
(or Peep will complain).

**Peep does not magically vet your packages.** Peep is not a substitute for
combing through your packages for malicious code or comparing them with
known-good versions. If you don't vet them, they are not vetted.

**Peep does not make authors or indices trustworthy.** All Peep does is
guarantee that subsequent downloads of ``Foo==1.2.3`` are the same as the
first one. It doesn't guarantee the author of that package is trustworthy. It
doesn't guarantee that the author of that package is the one who released that
package. It doesn't guarantee that the package index is trustworthy.


Troubleshooting
===============

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
to vet one of them (say, the tarball), then download the others and use a file
comparison tool to verify that they have identical contents. Then I run ``peep
hash`` over both original archives, like so, and add the result to my
``requirements.txt``::

    % peep hash mock-0.8.0.tar.gz mock-0.8.0.zip
    # sha256: lvpN706AIAvoJ8P1EUfdez-ohzuSB-MyXUe6Rb8ppcE
    # sha256: 6QTt-5DahBKcBiUs06BfkLTuvBu1uF7pblb_bPaUONU

Upgrading Wheels with Old Versions of pip
-----------------------------------------

If you're reusing a virtualenv and using Peep with pip <6.0, then you should
avoid using wheels. Otherwise, the old version of a package will not be entirely
removed before the new one is installed, due to
https://github.com/pypa/pip/issues/1825.

If you're using pip 1.4, don't pass the ``--use-wheel`` argument.

If you're using pip 1.5, pass the ``--no-use-wheel`` argument.


Version History
===============

3.1.2
  * Fix compatibility with pip 8.1.2. (abbeyj)

3.1.1
  * The "peep had a problem" traceback is no longer output for several cases
    of pip installation errors that were not peep's fault: for instance, the
    specified package version or requirements file not existing.
  * ``peep port`` now emits URLs for URL-based requirements, if you're using
    pip 6.1.0 or greater. (jotes)

3.1
  * Print the name each new requirements file we encounter during ``peep
    port``. This helps untangle the mess if your files use includes. (pmac)
  * Always put hashes on their own lines, even if there's only one. (pmac)

3.0
  * Add support for pip 8.x.
  * Drop support for the ``--allow-external``, ``--allow-unverified`` and
    ``--allow-all-external`` arguments (for compatibility with pip 8).
  * Drop support for Python 3.1/3.2.

2.5
  * Support pip 7.x, through the currently latest 7.1.2, working around its
    buggy line counting. (kouk)
  * Add ``peep port`` command to facilitate the transition to `pip 8's hashing
    <https://pip.pypa.io/en/latest/reference/pip_install/#hash-checking-mode>`_.
  * Fix bug in which the right way to call ``parse_requirements()`` would not
    be autodetected.

2.4.1
  * Tolerate pip.__version__ being missing, which can apparently happen in
    arcane situations during error handling, obscuring informative tracebacks.
  * Fix flake8 warnings again, and add flake8 to Travis runs.

2.4
  * Add support for flags in the requirements file, pip-style, such as
    specifying alternative indices with ``-i``.
  * Remove a duplicate ``#egg=`` segment from an error message.

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
