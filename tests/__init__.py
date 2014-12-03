from contextlib import contextmanager
from os import chdir, getcwd
from os.path import dirname, join
from shutil import rmtree
from SimpleHTTPServer import SimpleHTTPRequestHandler
import socket
from SocketServer import TCPServer
from pipes import quote
from subprocess import CalledProcessError, check_output
from tempfile import mkdtemp
from threading import Thread
from unittest import TestCase

from nose.tools import eq_, nottest

from peep import EmptyOptions, SOMETHING_WENT_WRONG, downloaded_reqs_from_path, MissingReq


@contextmanager
def ephemeral_dir():
    dir = mkdtemp(prefix='peep-')
    try:
        yield dir
    finally:
        rmtree(dir)


@contextmanager
def requirements(contents):
    """Return a path to a requirements.txt file of given contents.

    As long as the context manager is open, the requirements file will exist.

    """
    with ephemeral_dir() as temp_dir:
        path = join(temp_dir, 'reqs.txt')
        with open(path, 'w') as file:
            file.write(contents)
        yield path


def run(command, **kwargs):
    """Return the output of a command.

    Pass in any kind of shell-executable line you like, with one or more
    commands, pipes, etc. Any kwargs will be shell-escaped and then subbed into
    the command using ``format()``::

        >>> run('echo hi')
        "hi"
        >>> run('echo {name}', name='Fred')
        "Fred"

    This is optimized for callsite readability. Internalizing ``format()``
    keeps noise off the call. If you use named substitution tokens, individual
    commands are almost as readable as in a raw shell script. The command
    doesn't need to be read out of order, as with anonymous tokens.

    """
    return check_output(
        command.format(**dict((k, quote(v)) for k, v in kwargs.iteritems())),
        shell=True)


def python_path():
    # Not returning sys.executable, because that does the wrong thing for
    # venvs. This pretty much assumes we're running in a venv (which we
    # certainly should be). Improvements welcome.
    return 'python'


@nottest
def tests_dir():
    """Return a path to the "tests" directory."""
    return dirname(__file__)


def peep_path():
    """Return a path to peep.py."""
    return join(dirname(tests_dir()), 'peep.py')


class QuietRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Don't log each request to the terminal."""


class InstallTestCase(TestCase):
    """Tests which actually try installing a package"""

    @classmethod
    def setup_class(cls):
        # Just in case the env was left dirty:
        try:
            run('pip uninstall -y useless')
        except CalledProcessError as exc:  # happens when it's not installed
            pass


class ServerTestCase(InstallTestCase):
    """Tests which use an HTTP server serving a small, local index"""

    @classmethod
    def setup_class(cls):
        """Spin up an HTTP server pointing at a small, local package index."""
        super(ServerTestCase, cls).setup_class()

        cls.old_cwd = getcwd()
        chdir(join(tests_dir(), 'packages'))  # for the HTTP server

        # Find a port, and bind to it. I can't get the OS to close the socket
        # promptly after we shut down the server, so we typically need to try
        # a couple ports after the first test case. Setting
        # TCPServer.allow_reuse_address = True seems to have nothing to do
        # with this behavior.
        worked = False
        for port in xrange(8989, 8999):
            cls.port = port
            try:
                cls.server = TCPServer(('localhost', cls.port),
                                       QuietRequestHandler)
            except socket.error:
                pass
            else:
                worked = True
                break
        if not worked:
            raise RuntimeError("Couldn't find a socket to use for a temporary index server.")

        cls.thread = Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def teardown_class(cls):
        cls.server.shutdown()
        cls.thread.join()
        chdir(cls.old_cwd)

    @classmethod
    def index_url(cls):
        return 'http://localhost:{}/'.format(cls.port)


class FullStackTests(ServerTestCase):
    """Tests which run peep via the shell, as a separate process

    This is necessary because some of the internals of pip we call contain
    singletons and ruin themselves for future calls within one interpreter
    instance.

    """
    @classmethod
    def install_from_path(cls, reqs_path):
        """Install from a requirements file using peep, and return the result
        string.

        On failure, raise CalledProcessError.

        """
        return run('{python} {peep} install -r {reqs} --index-url {local}',
                   python=python_path(),
                   peep=peep_path(),
                   reqs=reqs_path,
                   local=cls.index_url())

    def install_from_string(cls, reqs):
        """Install from a string of requirements using peep, and return the
        result string.

        On failure, raise CalledProcessError.

        """
        with requirements(reqs) as reqs_path:
            cls.install_from_path(reqs_path)

    def test_success(self):
        """If a hash matches, peep should do its work and exit happily."""
        self.install_from_string(
            """# sha256: yy1CrBcHwIdIMUZGeg6blwoVuQ0bz8MnsPdhWxVoWFg
            useless==1.0""")
        # No exception raised == happiness.
        run('pip uninstall -y useless')

    def test_mismatch(self):
        """If a hash doesn't match, peep should explode."""
        try:
            self.install_from_string(
                """# sha256: badbadbad
                useless==1.0""")
        except CalledProcessError as exc:
            eq_(exc.returncode, SOMETHING_WENT_WRONG)
        else:
            self.fail("Peep exited successfully but shouldn't have.")

    def test_missing(self):
        """If a hash is missing, peep should explode."""
        try:
            self.install_from_string("""useless==1.0""")
        except CalledProcessError as exc:
            eq_(exc.returncode, SOMETHING_WENT_WRONG)
        else:
            self.fail("Peep exited successfully but shouldn't have.")


class HashParsingTests(ServerTestCase):
    """Tests for finding the hashes above each requirement"""

    def downloaded_reqs(self, text):
        """Return a list of DownloadedReqs based on a requirements file's
        text.

        The requirements must all point to packages in the local test index.

        """
        with requirements(text) as path:
            return downloaded_reqs_from_path(
                    path,
                    ['-r', path, '--index-url', self.index_url()])

    def test_inline_comments(self):
        """Make sure various permutations of inline comments are parsed
        correctly."""
        reqs = self.downloaded_reqs("""
                # sha256: t9XWiL3TRb-ol3d9KXdWaIzwLhs3QsVoheLlwrmW_4I  # hi
                useless==1.0
                # sha256:   some_number_######_signs # hi # there
                # sha256: abcde  # hi
                useless==1.0""")
        eq_(reqs[0]._expected_hashes(),
            ['t9XWiL3TRb-ol3d9KXdWaIzwLhs3QsVoheLlwrmW_4I'])
        eq_(reqs[1]._expected_hashes(),
            ['some_number_######_signs', 'abcde'])

    def test_missing_hashes(self):
        """Make sure we detect missing hashes."""
        reqs = self.downloaded_reqs("""
            # sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            useless==1.0
            useless==1.0""")
        eq_(reqs[1].__class__, MissingReq)

    def test_non_hash_comments(self):
        """Non-hash or malformed hash comments should be ignored."""
        reqs = self.downloaded_reqs("""
            # unknown_hash_type: t9XWiL3TRb-ol3d9KXdWaIzwLhs3QsVoheLlwrmW_4I
            # sha256: invalid hash with spaces  # hi mom
            # sha256: invalid hash with no comment
            useless==1.0
            # Just some comment
            # sha256: abc
            useless==1.0""")
        eq_(reqs[1]._expected_hashes(), ['abc'])

        # None of those bogus lines above MissingThing should have been
        # mistaken for a hash:
        eq_(reqs[0].__class__, MissingReq)

    def test_whitespace_stripping(self):
        """Make sure trailing whitespace is stripped from hashes."""
        reqs = self.downloaded_reqs("""
            # sha256: trailing_space_should_be_stripped   
            useless==1.0
            """)
        eq_(reqs[0]._expected_hashes(), ['trailing_space_should_be_stripped'])
