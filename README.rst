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

    -------------------------------
    Not proceeding to installation.
2. Vet the packages coming off PyPI in whatever way you typically do.
3. Add the recommended hash lines to your ``requirements.txt``, each one
   directly above the requirement it applies to. (The hashes are of the
   original, compressed tarballs from PyPI.)
4. In the future, always use ``peep install`` to install your requirements. You
   are now cryptographically safe!


The Fearsome Warning
====================

If, during installation, a hash doesn't match, ``peep`` will say something like
this::

    THE FOLLOWING PACKAGES DIDN'T MATCHES THE HASHES SPECIFIED IN THE
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


Troubleshooting
===============

Are you suddenly getting the Fearsome Warning? Maybe you're really in trouble,
but maybe something more innocuous is happening.

Some packages offer downloads in multiple formats: for example, zips and
tarballs. Pip is currently unpredictable in its choice of archive in such
situations. Thus, some packages have more than one valid hash for a given
version. To allow for these, you can stack up multiple known-good hashes above
a requirement, as long as they are within a contiguous block of commented
lines::

    # Tarball:
    # sha256: lvpN706AIAvoJ8P1EUfdez-ohzuSB-MyXUe6Rb8ppcE
    #
    # And the zip file:
    # sha256: 6QTt-5DahBKcBiUs06BfkLTuvBu1uF7pblb_bPaUONU
    mock==0.8.0

A future version of peep will emit all the applicable hashes as suggestions, to
save you the effort of manually identifying such packages. Or, more likely, we
will simply correct pip's capriciousness in a future version of it.
https://github.com/pypa/pip/issues/1194 is the bug to watch.


Version History
===============

0.5
  * Allow multiple acceptable hashes for a package. This works around pip's
    unpredictable treatment of packages like mock, which provide equivalent
    zips and tarballs: https://github.com/pypa/pip/issues/1194.

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
