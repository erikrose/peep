====
Peep
====

Historically, deploying Python projects has been a pain in the neck if you want
any kind of security. PyPI lets package authors change the contents of their
packages without revving the version number, and, until very recently, there
was no support for HTTPS, leaving it open to man-in-the-middle attacks. If you
wanted to guarantee known-good dependencies for your deployment, you had to
either run a local PyPI mirror, manually uploading packages as you vetted them,
or you had to check everything into a vendor library, necessitating a lot of
fooling around with your VCS (or maintaining custom tooling) to do upgrades.

Peep fixes all that.

Vet your packages, put hashes of the PyPI-sourced tarballs into
requirements.txt, use ``peep install`` instead of ``pip install``, and let the
crypto do the rest. If a downloaded package doesn't match the hash, Peep will
freak out, and installation will go no further. No servers to maintain, no
enormous vendor libs to wrestle. Just requirements.txt with some funny-looking
comments and peace of mind.


Version History
===============

0.1
  * Proof of concept. Does all the crypto stuff. Should be secure. Some rough
    edges in the UI.
