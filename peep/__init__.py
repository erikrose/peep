"""peep ("prudently examine every package") verifies that packages conform to a
trusted, locally stored hash and only then installs them::

    peep install -r requirements.txt

This makes your deployments verifiably repeatable without having to maintain a
local PyPI mirror or use a vendor lib. Just update the version numbers and
hashes in requirements.txt, and you're all set.

"""
from base64 import urlsafe_b64encode
from contextlib import contextmanager
from hashlib import sha256
from linecache import getline
from optparse import OptionParser
from os import listdir
from os.path import join
import re
from shutil import rmtree
from sys import argv, exit
from tempfile import mkdtemp

import pip
from pip.log import logger
from pip.req import parse_requirements


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
    return urlsafe_b64encode(sha.digest()).rstrip('=')


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


def pip_download(argv, temp_path):
    """Download packages to the dir specified by ``temp_path``."""
    argv = argv[1:]  # copy and strip off binary name
    argv[1:1] = ['--no-deps', '--download', temp_path]
    # pip downloads the tarball into a second temp dir it creates, then it
    # copies it to our specified download dir, then it unpacks it into the
    # build dir in the venv (probably to read metadata out of it), then it
    # deletes that. Don't be afraid: the tarball we're hashing is the pristine
    # one downloaded from PyPI, not a fresh tarring of unpacked files.
    run_pip(argv)


def pip_install_archives_from(temp_path):
    """pip install the archives from the ``temp_path`` dir, omitting
    dependencies."""
    # TODO: Make this preserve any pip options passed in, but strip off -r
    # options and other things that don't make sense at this point in the
    # process.
    for filename in listdir(temp_path):
        archive_path = join(temp_path, filename)
        run_pip(['install', '--no-deps', archive_path])


def package_from_filename(filename):
    return filename[:filename.rindex('-')]  # TODO: Does this always work?


def hashes_of_downloads(temp_path):
    """Return a dict of package names pointing to the hashes of their
    archives."""
    ret = {}
    for filename in listdir(temp_path):
        with open(join(temp_path, filename), 'r') as archive:
            sha = sha256()
            while True:
                data = archive.read(2 ** 20)
                if not data:
                    break
                sha.update(data)
        ret[package_from_filename(filename)] = encoded_hash(sha)
    return ret


def versions_of_downloads(temp_path):
    """Return a dict of package names pointing to version numbers."""
    def version_from_filename(filename):
        """Return the version number of a PEP-386-compliant package, given its
        archive filename.

        If the version number can't be determined, return ''.

        """
        _, right_of_dash = filename.rsplit('-', 1)
        match = re.match(r'([0-9]+(?:\.[0-9]+){1,2}(?:[ab][0-9]+)?)'
                         r'\.(?:tar\.gz|tgz|tar|zip)',
                         right_of_dash)  # leaning on regex cache here
        if match:
            return match.group(1)
        return ''

    ret = {}
    for filename in listdir(temp_path):
        ret[package_from_filename(filename)] = version_from_filename(filename)
    return ret


def requirement_paths(argv):
    """Return a list of paths to requirements files from the args.

    If none, return [].

    """
    was_r = False
    ret = []
    for arg in argv[1:]:
        # Allow for requirements files named "-r", don't freak out if there's a
        # trailing "-r", etc.
        if was_r:
            ret.append(arg)
            was_r = False
        elif arg in ['-r', '--requirement']:
            was_r = True
    return ret


def hashes_of_requirements(paths):
    """Return a map of package names to expected hashes, given multiple
    requirements files."""
    def path_and_line(req):
        """Return the path and line number of the file from which an
        InstallRequirement came."""
        path, line = (re.match(r'-r (.*) \(line (\d+)\)$',
                      req.comes_from).groups())
        return path, int(line)

    expected_hashes = {}
    missing_hashes = []

    for path in paths:
        reqs = parse_requirements(path)
        for req in reqs:  # InstallRequirements
            path, line_number = path_and_line(req)
            if line_number > 1:
                previous_line = getline(path, line_number - 1)
                if previous_line.startswith('# sha256: '):
                    expected_hashes[req.name] = previous_line.split(':', 1)[1].strip()
                    continue
            missing_hashes.append(req.name)
    return expected_hashes, missing_hashes


def hash_mismatches(expected_hashes, downloaded_hashes):
    """Yield the expected hash, package name, and download-hash of each
    package whose download-hash didn't match the one specified for it in the
    requirments file."""
    for package_name, expected_hash in expected_hashes.iteritems():
        hash_of_download = downloaded_hashes[package_name]
        if hash_of_download != expected_hash:
            yield expected_hash, package_name, hash_of_download


def main():
    """Implement "peep install". Return a shell status code."""
    ITS_FINE_ITS_FINE = 0
    SOMETHING_WENT_WRONG = 1
    # "Traditional" for command-line errors according to optparse docs:
    COMMAND_LINE_ERROR = 2

    try:
        if not (len(argv) >= 2 and argv[1] == 'install'):
            # Fall through to top-level pip main() for everything else:
            return pip.main()

        req_paths = requirement_paths(argv)
        if not req_paths:
            print "You have to specify one or more requirements files with the -r option, because otherwise there's nowhere for peep to look up the hashes."
            return COMMAND_LINE_ERROR

        # We're a "peep install" command, and we have some requirement paths.
        with ephemeral_dir() as temp_path:
            pip_download(argv, temp_path)
            downloaded_hashes = hashes_of_downloads(temp_path)
            downloaded_versions = versions_of_downloads(temp_path)
            expected_hashes, missing_hashes = hashes_of_requirements(req_paths)
            mismatches = list(hash_mismatches(expected_hashes, downloaded_hashes))

            # Skip a line after pip's "Cleaning up..." so the important stuff
            # stands out:
            if mismatches or missing_hashes:
                print

            # Mismatched hashes:
            if mismatches:
                print "THE FOLLOWING PACKAGES DIDN'T MATCHES THE HASHES SPECIFIED IN THE REQUIREMENTS FILE. If you have updated the package versions, update the hashes. If not, freak out, because someone has tampered with the packages.\n"
            for expected_hash, package_name, hash_of_download in mismatches:
                hash_of_download = downloaded_hashes[package_name]
                if hash_of_download != expected_hash:
                    print '    %s: expected %s' % (
                            package_name,
                            expected_hash)
                    print ' ' * (5 + len(package_name)), '     got', hash_of_download
            if mismatches:
                print  # Skip a line before "Not proceeding..."

            # Missing hashes:
            if missing_hashes:
                print 'The following packages had no hashes specified in the requirements file, which leaves them open to tampering. Vet these packages to your satisfaction, then add these "sha256" lines like so:\n'
            for package_name in missing_hashes:
                print '    # sha256: %s' % downloaded_hashes[package_name]
                print '    %s==%s\n' % (package_name,
                                        downloaded_versions[package_name] or
                                            'x.y.z')

            if mismatches or missing_hashes:
                print 'Not proceeding to installation.'
                return SOMETHING_WENT_WRONG
            else:
                pip_install_archives_from(temp_path)
    except PipException as exc:
        return exc.error_code
    return ITS_FINE_ITS_FINE
