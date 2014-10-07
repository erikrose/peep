from contextlib import contextmanager
from os.path import join
from unittest import TestCase

from nose.tools import eq_

from peep import EmptyOptions, ephemeral_dir, hashes_of_requirements
from pip.req import parse_requirements


@contextmanager
def requirements(contents):
    """Return an iterable of InstallRequirements parsed from contents of a
    requirements.txt file.

    As long as the context manager is open, the requirements file will exist.
    This comes in handy for hashes_of_requirements(), which peeks back at the
    file.

    """
    with ephemeral_dir() as temp_dir:
        path = join(temp_dir, 'reqs.txt')
        with open(path, 'w') as file:
            file.write(contents)
        yield parse_requirements(path, options=EmptyOptions())


def hashes_of_ephemeral_requirements(contents):
    """Return the results of hashes_of_requirements() as if passed a
    requirements file with the given contents."""
    with requirements(contents) as reqs:
        return hashes_of_requirements(reqs)


class HashesOfRequirementsTests(TestCase):
    """Tests for hashes_of_requirements()"""

    def test_inline_comments(self):
        """Make sure various permutations of inline comments are parsed
        correctly."""
        expected, missing = hashes_of_ephemeral_requirements("""
            # sha256: t9XWiL3TRb-ol3d9KXdWaIzwLhs3QsVoheLlwrmW_4I  # hi
            MarkupSafe==0.1
            # sha256:   some_number_######_signs # hi # there
            # sha256: abcde  # hi
            MarkupDangerous==0.2""")
        eq_(expected,
            {'MarkupSafe': ['t9XWiL3TRb-ol3d9KXdWaIzwLhs3QsVoheLlwrmW_4I'],
             'MarkupDangerous': ['some_number_######_signs', 'abcde']})
        eq_(missing, [])

    def test_missing_hashes(self):
        """Make sure we detect missing hashes."""
        expected, missing = hashes_of_ephemeral_requirements("""
            # sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            howdyDudley==0.1
            MarkupRisky==0.2""")
        eq_(len(missing), 1)
        eq_(missing[0].name, 'MarkupRisky')

    def test_non_hash_comments(self):
        """Non-hash or malformed hash comments should be ignored."""
        expected, missing = hashes_of_ephemeral_requirements("""
            # unknown_hash_type: t9XWiL3TRb-ol3d9KXdWaIzwLhs3QsVoheLlwrmW_4I
            # sha256: invalid hash with spaces  # hi mom
            # sha256: invalid hash with no comment
            MissingThing==0.1
            # Just some comment
            # sha256: abc
            MarkupDangerous==0.2""")
        eq_(expected, {'MarkupDangerous': ['abc']})
        
        # None of those bogus lines above MissingThing should have been
        # mistaken for a hash:
        eq_(len(missing), 1)
        eq_(missing[0].name, 'MissingThing')

    def test_whitespace_stripping(self):
        """Make sure trailing whitespace is stripped from hashes."""
        expected, missing = hashes_of_ephemeral_requirements("""
            # sha256: trailing_space_should_be_stripped       
            MarkupDangerous==0.2
            """)
        eq_(expected, {'MarkupDangerous': ['trailing_space_should_be_stripped']})
        eq_(missing, [])
