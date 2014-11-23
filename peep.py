#!/usr/bin/env python
"""peep ("prudently examine every package") verifies that packages conform to a
trusted, locally stored hash and only then installs them::

    peep install -r requirements.txt

This makes your deployments verifiably repeatable without having to maintain a
local PyPI mirror or use a vendor lib. Just update the version numbers and
hashes in requirements.txt, and you're all set.

"""
from __future__ import print_function
from base64 import urlsafe_b64encode
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
from hashlib import sha256
from itertools import chain
from linecache import getline
from optparse import OptionParser
from os import listdir
from os.path import join, basename, splitext
import re
import shlex
from shutil import rmtree
from sys import argv, exit
from tempfile import mkdtemp
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse  # 3.4

from pkg_resources import require, VersionConflict, DistributionNotFound

# We don't admit our dependency on pip in setup.py, lest a naive user simply
# say `pip install peep.tar.gz` and thus pull down an untrusted copy of pip
# from PyPI. Instead, we make sure it's installed and new enough here and spit
# out an error message if not:
def activate(specifier):
    """Make a compatible version of pip importable. Raise a RuntimeError if we
    couldn't."""
    try:
        for distro in require(specifier):
            distro.activate()
    except (VersionConflict, DistributionNotFound):
        raise RuntimeError('The installed version of pip is too old; peep '
                           'requires ' + specifier)

activate('pip>=0.6.2')  # Before 0.6.2, the log module wasn't there, so some
                        # of our monkeypatching fails. It probably wouldn't be
                        # much work to support even earlier, though.

import pip
from pip.log import logger
from pip.req import parse_requirements


__version__ = 2, 0, 0


ITS_FINE_ITS_FINE = 0
SOMETHING_WENT_WRONG = 1
# "Traditional" for command-line errors according to optparse docs:
COMMAND_LINE_ERROR = 2

ARCHIVE_EXTENSIONS = ('.tar.bz2', '.tar.gz', '.tgz', '.tar', '.zip')


class PipException(Exception):
    """When I delegated to pip, it exited with an error."""

    def __init__(self, error_code):
        self.error_code = error_code


def encoded_hash(sha):
    """Return a short, 7-bit-safe representation of a hash.

    If you pass a sha256, this results in the hash algorithm that the Wheel
    format (PEP 427) uses, except here it's intended to be run across the
    downloaded archive before unpacking.

    """
    return urlsafe_b64encode(sha.digest()).decode('ascii').rstrip('=')


@contextmanager
def ephemeral_dir():
    dir = mkdtemp(prefix='peep-')
    try:
        yield dir
    finally:
        rmtree(dir)


def run_pip(initial_args):
    """Delegate to pip the given args (starting with the subcommand), and raise
    ``PipException`` if something goes wrong."""
    status_code = pip.main(initial_args=initial_args)

    # Clear out the registrations in the pip "logger" singleton. Otherwise,
    # loggers keep getting appended to it with every run. Pip assumes only one
    # command invocation will happen per interpreter lifetime.
    logger.consumers = []

    if status_code:
        raise PipException(status_code)


# Based on req_set.prepare_files() in pip bb2a8428d4aebc8d313d05d590f386fa3f0bbd0f
# finder = PackageFinder(
#             find_links=options.find_links,
#             index_urls=index_urls,
#             use_wheel=options.use_wheel,
#             allow_external=options.allow_external,
#             allow_unverified=options.allow_unverified,
#             allow_all_external=options.allow_all_external,
#             allow_all_prereleases=options.pre,
#             process_dependency_links=options.process_dependency_links,
#             session=session,
#         )  # That's true in both wheel and non-wheel installs.
# dependency_links are okay; those are just additional web page URLs to check.
# Maybe delete stuff that doesn't make any sense in a peep context, like things that deal with package upgrades (of already satisfied requirements), which shouldn't happen for ==-style requirements. I suspect our decisions about satisfiedness are already made by the time we hit this, by DownloadedReq.
def prepare_files(requirements, finder, ignore_installed, editable, force_reinstall, upgrade, use_user_site, src_dir, build_dir, download_dir, wheel_download_dir, session):
    # Previously: Prepare process. Create temp directories, download and/or unpack files.
    """Download all necessary files for each requirement.
    
    Somebody else can figure out how to hash and compare them.
    
    """
    # Based on is_download()
    def download_dir_exists(download_dir):
        """Return whether an existent download dir is given, and normalize it."""
        if download_dir:
            download_dir = os.path.expanduser(download_dir)
            if os.path.exists(download_dir):
                return download_dir, True
            else:
                logger.critical('Could not find download directory')
                raise InstallationError(
                    "Could not find or access download directory '%s'"
                    % display_path(download_dir))
        return download_dir, False

    download_dir, is_download = download_dir_exists(download_dir)

    for req_to_install in requirements:
        install = True
        best_installed = False
        not_found = None

        # ############################################# #
        # # Search for archive to fulfill requirement # #
        # ############################################# #

        if not ignore_installed and not req_to_install.editable:
            req_to_install.check_if_exists()
            if req_to_install.satisfied_by:
#                 if upgrade:
#                     if not force_reinstall and not req_to_install.url:
#                         try:
#                             url = finder.find_requirement(
#                                 req_to_install, upgrade)
#                         except BestVersionAlreadyInstalled:
#                             best_installed = True
#                             install = False
#                         except DistributionNotFound as exc:
#                             not_found = exc
#                         else:
#                             # Avoid the need to call find_requirement again
#                             req_to_install.url = url.url
# 
#                     if not best_installed:
#                         # don't uninstall conflict if user install and
#                         # conflict is not user install
#                         if not (use_user_site
#                                 and not dist_in_usersite(
#                                     req_to_install.satisfied_by
#                                 )):
#                             req_to_install.conflicts_with = \
#                                 req_to_install.satisfied_by
#                         req_to_install.satisfied_by = None
#                 else:
                    install = False
            if req_to_install.satisfied_by:
#                 if best_installed:
#                     logger.info(
#                         'Requirement already up-to-date: %s',
#                         req_to_install,
#                     )
#                 else:
#                     logger.info(
#                         'Requirement already satisfied (use --upgrade to '
#                         'upgrade): %s',
#                         req_to_install,
#                     )
        if req_to_install.editable:
            logger.info('Obtaining %s', req_to_install)
        elif install:
            if (req_to_install.url
                    and req_to_install.url.lower().startswith('file:')):
                logger.info(
                    'Unpacking %s',
                    display_path(url_to_path(req_to_install.url)),
                )
            else:
                logger.info('Downloading/unpacking %s', req_to_install)

        with indent_log():
            # ################################ #
            # # vcs update or unpack archive # #
            # ################################ #

            is_wheel = False
            if req_to_install.editable:
                if req_to_install.source_dir is None:
                    location = req_to_install.build_location(src_dir)
                    req_to_install.source_dir = location
                else:
                    location = req_to_install.source_dir
                if not os.path.exists(build_dir):
                    _make_build_dir(build_dir)
                req_to_install.update_editable(not is_download)  # vcs checkouts and file:// URLs
                if is_download:
                    req_to_install.run_egg_info()  # HOLY CRAP DON'T DO THIS unless we can git fsck the download or something. Or maybe git against remote servers is trustworthy now: http://www.mythmon.com/posts/malicious-git-servers.html.
                    req_to_install.archive(download_dir)
                else:
                    req_to_install.run_egg_info()  # HOLY CRAP DON'T DO THIS
            elif install:
                # @@ if filesystem packages are not marked
                # editable in a req, a non deterministic error
                # occurs when the script attempts to unpack the
                # build directory

                # NB: This call can result in the creation of a temporary
                # build directory
                location = req_to_install.build_location(
                    build_dir,
                    not is_download,
                )
                unpack = True
                url = None

                # If a checkout exists, it's unwise to keep going.  version
                # inconsistencies are logged later, but do not fail the
                # installation.
                if os.path.exists(os.path.join(location, 'setup.py')):
                    raise PreviousBuildDirError(
                        "pip can't proceed with requirements '%s' due to a"
                        " pre-existing build directory (%s). This is "
                        "likely due to a previous installation that failed"
                        ". pip is being responsible and not assuming it "
                        "can delete this. Please delete it and try again."
                        % (req_to_install, location)
                    )
                else:
                    # FIXME: this won't upgrade when there's an existing
                    # package unpacked in `location`
                    if req_to_install.url is None:
                        if not_found:
                            raise not_found
                        url = finder.find_requirement(
                            req_to_install,
                            upgrade=upgrade,
                        )
                    else:
                        # FIXME: should req_to_install.url already be a
                        # link?
                        url = Link(req_to_install.url)
                        assert url
                    if url:
                        try:

                            if (
                                url.filename.endswith(wheel_ext)
                                and wheel_download_dir
                            ):
                                # when doing 'pip wheel`
                                download_dir = wheel_download_dir
                                do_download = True
                            else:
                                download_dir = download_dir
                                do_download = is_download
                            unpack_url(
                                url, location, download_dir,
                                do_download, session=session,
                            )
                        except requests.HTTPError as exc:
                            logger.critical(
                                'Could not install requirement %s because '
                                'of error %s',
                                req_to_install,
                                exc,
                            )
                            raise InstallationError(
                                'Could not install requirement %s because '
                                'of HTTP error %s for URL %s' %
                                (req_to_install, exc, url)
                            )
                    else:
                        unpack = False
                # All we probably need from here down (and maybe not even this) is to zip up any VCS-checked-out requirements so they can be pip installed later. We don't care about assert_source_matches_version() or .satisfied_by, because we ensure accuracy by comparing hashes externally, and we deal with satisfaction externally as well.
                if unpack:
                    is_wheel = url and url.filename.endswith(wheel_ext)
                    if is_download:
                        req_to_install.source_dir = location
                        if not is_wheel:
                            # FIXME:https://github.com/pypa/pip/issues/1112
                            req_to_install.run_egg_info()  # NOPE NOPE NOPE
                        if url and url.scheme in vcs.all_schemes:
                            req_to_install.archive(download_dir)
                    elif is_wheel:
                        req_to_install.source_dir = location
                        req_to_install.url = url.url
                    else:
                        req_to_install.source_dir = location
                        req_to_install.run_egg_info()  # NOPE
                        req_to_install.assert_source_matches_version()
                    # req_to_install.req is only avail after unpack for URL
                    # pkgs repeat check_if_exists to uninstall-on-upgrade
                    # (#14)
                    if not ignore_installed:
                        req_to_install.check_if_exists()
                    if req_to_install.satisfied_by:
                        if upgrade or ignore_installed:
                            # don't uninstall conflict if user install and
                            # conflict is not user install
                            if not (use_user_site
                                    and not dist_in_usersite(
                                        req_to_install.satisfied_by)):
                                req_to_install.conflicts_with = \
                                    req_to_install.satisfied_by
                            req_to_install.satisfied_by = None
                        else:
                            logger.info(
                                'Requirement already satisfied (use '
                                '--upgrade to upgrade): %s',
                                req_to_install,
                            )
                            install = False


def download(requirements_path, line_number, temp_path):
    """Download a package, and return its filename.

    :arg argv: Arguments to be passed along to pip, starting after the
        subcommand
    :arg temp_path: The path to the directory to download to

    """
    # Get the original line out of the reqs file:
    line = getline(requirements_path, line_number)

    argv = []

    # Remove any requirement file args.
    argv = (['install', '--no-deps', '--download', temp_path] +
            list(requirement_args(argv, want_other=True)) +  # other args
            shlex.split(line))  # ['nose==1.3.0']. split() removes trailing \n.

    # Remember what was in the dir so we can backtrack and tell what we've
    # downloaded (disgusting):
    old_contents = set(listdir(temp_path))

    # pip downloads the tarball into a second temp dir it creates, then it
    # copies it to our specified download dir, then it unpacks it into the
    # build dir in the venv (probably to read metadata out of it), then it
    # deletes that. Don't be afraid: the tarball we're hashing is the pristine
    # one downloaded from PyPI, not a fresh tarring of unpacked files.
    run_pip(argv)

    new = set(listdir(temp_path)) - old_contents
    if len(new) != 1:
        raise RuntimeError("Somebody threw a file into my temp dir while I was working in there.")
    return new.pop()


def pip_install_archives_from(temp_path, argv):
    """pip install the archives from the ``temp_path`` dir, omitting
    dependencies."""
    other_args = list(requirement_args(argv, want_other=True))
    for filename in listdir(temp_path):
        archive_path = join(temp_path, filename)
        run_pip(['install'] + other_args +  ['--no-deps', archive_path])


def hash_of_file(path):
    """Return the hash of a downloaded file."""
    with open(path, 'rb') as archive:
        sha = sha256()
        while True:
            data = archive.read(2 ** 20)
            if not data:
                break
            sha.update(data)
    return encoded_hash(sha)


def is_git_sha(text):
    """Return whether this is probably a git sha"""
    # Handle both the full sha as well as the 7-character abbrviation
    if len(text) in (40, 7):
        try:
            int(text, 16)
            return True
        except ValueError:
            pass
    return False


def filename_from_url(url):
    parsed = urlparse(url)
    path = parsed.path
    return path.split('/')[-1]


def requirement_args(argv, want_paths=False, want_other=False):
    """Return an iterable of filtered arguments.

    :arg want_paths: If True, the returned iterable includes the paths to any
        requirements files following a ``-r`` or ``--requirement`` option.
    :arg want_other: If True, the returned iterable includes the args that are
        not a requirement-file path or a ``-r`` or ``--requirement`` flag.

    """
    was_r = False
    for arg in argv:
        # Allow for requirements files named "-r", don't freak out if there's a
        # trailing "-r", etc.
        if was_r:
            if want_paths:
                yield arg
            was_r = False
        elif arg in ['-r', '--requirement']:
            was_r = True
        else:
            if want_other:
                yield arg


HASH_COMMENT_RE = re.compile(
    r"""
    \s*\#\s+                   # Lines that start with a '#'
    (?P<hash_type>sha256):\s+  # Hash type is hardcoded to be sha256 for now.
    (?P<hash>[^\s]+)           # Hashes can be anything except '#' or spaces.
    \s*                        # Suck up whitespace before the comment or
                               #   just trailing whitespace if there is no
                               #   comment. Also strip trailing newlines.
    (?:\#(?P<comment>.*))?     # Comments can be anything after a whitespace+#
    $""", re.X)                #   and are optional.


def peep_hash(argv):
    """Return the peep hash of one or more files, returning a shell status code
    or raising a PipException.

    :arg argv: The commandline args, starting after the subcommand

    """
    parser = OptionParser(
        usage='usage: %prog hash file [file ...]',
        description='Print a peep hash line for one or more files: for '
                    'example, "# sha256: '
                    'oz42dZy6Gowxw8AelDtO4gRgTW_xPdooH484k7I5EOY".')
    _, paths = parser.parse_args(args=argv)
    if paths:
        for path in paths:
            print('# sha256:', hash_of_file(path))
        return ITS_FINE_ITS_FINE
    else:
        parser.print_usage()
        return COMMAND_LINE_ERROR


class EmptyOptions(object):
    """Fake optparse options for compatibility with pip<1.2

    pip<1.2 had a bug in parse_requirments() in which the ``options`` kwarg
    was required. We work around that by passing it a mock object.

    """
    default_vcs = None
    skip_requirements_regex = None


def memoize(func):
    cache = []

    @wraps(func)
    def memoizer(self):
        if not cache:
            cache.append(func(self))
        return cache[0]
    return memoizer


class DownloadedReq(object):
    """A wrapper around InstallRequirement which offers additional information
    based on downloading and examining a corresponding package archive

    These are conceptually immutable, so we can get away with memoizing
    expensive things.

    """
    def __init__(self, req, temp_path):
        """Download a requirement, compare its hashes, and return a subclass
        of DownloadedReq depending on its state.

        :arg req: The InstallRequirement I am based on
        :arg temp_path: A path to a temp dir in which to store downloads

        """
        self.req = req
        self.temp_path = temp_path
        self.__class__ = self._class()

    def _version(self):
        """Deduce the version number of the downloaded package from its filename."""
        def version_of_archive(filename, package_name):
            # Since we know the project_name, we can strip that off the left, strip
            # any archive extensions off the right, and take the rest as the
            # version.
            for ext in ARCHIVE_EXTENSIONS:
                if filename.endswith(ext):
                    filename = filename[:-len(ext)]
                    break
            # Handle github sha tarball downloads.
            if is_git_sha(filename):
                filename = package_name + '-' + filename
            if not filename.lower().replace('_', '-').startswith(package_name.lower()):
                # TODO: Should we replace runs of [^a-zA-Z0-9.], not just _, with -?
                give_up(filename, package_name)
            return filename[len(package_name) + 1:]  # Strip off '-' before version.

        def version_of_wheel(filename, package_name):
            # For Wheel files (http://legacy.python.org/dev/peps/pep-0427/#file-
            # name-convention) we know the format bits are '-' separated.
            whl_package_name, version, _rest = filename.split('-', 2)
            # Do the alteration to package_name from PEP 427:
            our_package_name = re.sub(r'[^\w\d.]+', '_', package_name, re.UNICODE)
            if whl_package_name != our_package_name:
                give_up(filename, whl_package_name)
            return version

        def give_up(filename, package_name):
            raise RuntimeError("The archive '%s' didn't start with the package name '%s', so I couldn't figure out the version number. My bad; improve me." %
                               (filename, package_name))

        return (version_of_wheel if self._download_filename().endswith('.whl')
                else version_of_archive)(self._download_filename(),
                                         self._project_name())

    def _is_always_unsatisfied(self):
        """Returns whether this requirement is always unsatisfied

        This would happen in cases where we can't determine the version
        from the filename.

        """
        # If this is a github sha tarball, then it is always unsatisfied
        # because the url has a commit sha in it and not the version
        # number.
        url = self.req.url
        if url:
            filename = filename_from_url(url)
            if filename.endswith(ARCHIVE_EXTENSIONS):
                filename, ext = splitext(filename)
                if is_git_sha(filename):
                    return True
        return False

    def _path_and_line(self):
        """Return the path and line number of the file from which our
        InstallRequirement came.

        """
        path, line = (re.match(r'-r (.*) \(line (\d+)\)$',
                      self.req.comes_from).groups())
        return path, int(line)

    @memoize  # Avoid hitting the file[cache] over and over.
    def _expected_hashes(self):
        """Return a list of known-good hashes for this package."""

        def hashes_above(path, line_number):
            """Yield hashes from contiguous comment lines before line
            ``line_number``.
            
            """
            for line_number in xrange(line_number - 1, 0, -1):
                line = getline(path, line_number)
                match = HASH_COMMENT_RE.match(line)
                if match:
                    yield match.groupdict()['hash']
                elif not line.lstrip().startswith('#'):
                    # If we hit a non-comment line, abort
                    break

        hashes = list(hashes_above(*self._path_and_line()))
        hashes.reverse()  # because we read them backwards
        return hashes

    @memoize  # Avoid re-downloading.
    def _download_filename(self):
        """Download the package's archive if necessary, and return its filename."""
        path, line = self._path_and_line()
        return download(path, line, self.temp_path)

    @memoize
    def _actual_hash(self):
        """Download the package's archive if necessary, and return its hash."""
        return hash_of_file(join(self.temp_path, self._download_filename()))

    def _project_name(self):
        """Return the inner Requirement's "unsafe name".

        Raise ValueError if there is no name.

        """
        name = getattr(self.req.req, 'project_name', '')
        if name:
            return name
        raise ValueError('Requirement has no project_name.')

    def _name(self):
        return self.req.name

    def _url(self):
        return self.req.url

    @memoize  # Avoid re-running expensive check_if_exists().
    def _is_satisfied(self):
        self.req.check_if_exists()
        return (self.req.satisfied_by and
                not self._is_always_unsatisfied())

    def _class(self):
        """Return the class I should be, spanning a continuum of goodness."""
        try:
            self._project_name()
        except ValueError:
            return MalformedReq
        if self._is_satisfied():
            return SatisfiedReq
        if not self._expected_hashes():
            return MissingReq
        if self._actual_hash() not in self._expected_hashes():
            return MismatchedReq
        return InstallableReq

    @classmethod
    def foot(cls):
        return ''


class MalformedReq(DownloadedReq):
    """A requirement whose package name could not be determined"""

    @classmethod
    def head(cls):
        return 'The following requirements could not be processed:\n'

    def error(self):
        return '* Unable to determine package name from URL %s; add #egg=' % self._url()


class MissingReq(DownloadedReq):
    """A requirement for which no hashes were specified in the requirements file"""

    @classmethod
    def head(cls):
        return ('The following packages had no hashes specified in the requirements file, which\n'
                'leaves them open to tampering. Vet these packages to your satisfaction, then\n'
                'add these "sha256" lines like so:\n\n')

    def error(self):
        if self._url():
            line = self._url()
            if self._name() not in filename_from_url(self._url()):
                line = '%s#egg=%s' % (line, self._name())
        else:
            line = '%s==%s' % (self._name(), self._version())
        return '# sha256: %s\n%s\n' % (self._actual_hash(), line)


class MismatchedReq(DownloadedReq):
    """A requirement for which the downloaded file didn't match any of my hashes."""
    @classmethod
    def head(cls):
        return ("THE FOLLOWING PACKAGES DIDN'T MATCH THE HASHES SPECIFIED IN THE REQUIREMENTS\n"
                "FILE. If you have updated the package versions, update the hashes. If not,\n"
                "freak out, because someone has tampered with the packages.\n\n")

    def error(self):
        preamble = '    %s: expected%s' % (
                self._project_name(),
                ' one of' if len(self._expected_hashes()) > 1 else '')
        return '%s %s\n%s got %s' % (
            preamble,
            ('\n' + ' ' * (len(preamble) + 1)).join(self._expected_hashes()),
            ' ' * (len(preamble) - 4),
            self._actual_hash())

    @classmethod
    def foot(cls):
        return '\n'


class SatisfiedReq(DownloadedReq):
    """A requirement which turned out to be already installed"""

    @classmethod
    def head(cls):
        return ("These packages were already installed, so we didn't need to download or build\n"
                "them again. If you installed them with peep in the first place, you should be\n"
                "safe. If not, uninstall them, then re-attempt your install with peep.\n")

    def error(self):
        return '   %s' % (self.req,)


class InstallableReq(DownloadedReq):
    """A requirement whose hash matched and can be safely installed"""


# DownloadedReq subclasses that indicate an error that should keep us from
# going forward with installation, in the order in which their errors should
# be reported:
ERROR_CLASSES = [MismatchedReq, MissingReq, MalformedReq]


def bucket(things, key):
    """Return a map of key -> list of things."""
    ret = defaultdict(list)
    for thing in things:
        ret[key(thing)].append(thing)
    return ret


def first_every_last(iterable, first, every, last):
    """Execute something before the first item of iter, something else for each
    item, and a third thing after the last.

    If there are no items in the iterable, don't execute anything.

    """
    did_first = False
    for item in iterable:
        if not did_first:
            first(item)
        every(item)
    if did_first:
        last(item)


def peep_install(argv):
    """Perform the ``peep install`` subcommand, returning a shell status code
    or raising a PipException.

    :arg argv: The commandline args, starting after the subcommand

    """
    output = []
    out = output.append
    try:
        req_paths = list(requirement_args(argv, want_paths=True))
        if not req_paths:
            out("You have to specify one or more requirements files with the -r option, because\n")
            out("otherwise there's nowhere for peep to look up the hashes.\n")
            return COMMAND_LINE_ERROR

        with ephemeral_dir() as temp_path:
            # We're a "peep install" command, and we have some requirement paths.
            reqs = chain.from_iterable(
                parse_requirements(path, options=EmptyOptions())
                for path in req_paths)
            reqs = [DownloadedReq(req, temp_path) for req in reqs]
            buckets = bucket(reqs, lambda r: r.__class__)

            # Skip a line after pip's "Cleaning up..." so the important stuff
            # stands out:
            if any(buckets[b] for b in ERROR_CLASSES):
                out('\n')

            printers = (lambda r: out(r.head()),
                        lambda r: out(r.error() + '\n'),
                        lambda r: out(r.foot()))
            for c in ERROR_CLASSES:
                first_every_last(buckets[c], *printers)

            if any(buckets[b] for b in ERROR_CLASSES):
                out('-------------------------------\n')
                out('Not proceeding to installation.\n')
                return SOMETHING_WENT_WRONG
            else:
                pip_install_archives_from(temp_path, argv)

                first_every_last(buckets[SatisfiedReq], *printers)

        return ITS_FINE_ITS_FINE
    finally:
        print(''.join(output))


def main():
    """Be the top-level entrypoint. Return a shell status code."""
    commands = {'hash': peep_hash,
                'install': peep_install}
    try:
        if len(argv) >= 2 and argv[1] in commands:
            return commands[argv[1]](argv[2:])
        else:
            # Fall through to top-level pip main() for everything else:
            return pip.main()
    except PipException as exc:
        return exc.error_code


if __name__ == '__main__':
    exit(main())
