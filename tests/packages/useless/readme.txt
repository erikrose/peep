=======================
Files in this directory
=======================

useless-1.0.tar.gz
  A package that is installed as a test. It has a specially instrumented
  setup.py file that drops a file on disk which the test harness can then read
  to determine whether the setup script has run.

useless-2.0.tar.gz
  A decoy to tempt ``pip install -U ...`` into downloading and installing a
  newer version of the "useless" package than the tarball we point it to

1234567.zip
  Another version of "useless", packaged up as if it were a GitHub-hosted zip
  file. It contains a ``useless.git_hash`` var which we check to make sure
  the right version got installed. It lacks the need for the TELLTALE env var
  to be set.

789abcd.zip
  The same as 1234567.zip except with a different value of
  ``useless.git_hash``. Has the same version number.
