from commands import getoutput
import logging
import os
import re
import sys
import zest.releaser.utils

logger = logging.getLogger('vcs')


class BaseVersionControl(object):
    "Shared implementation between all version control systems"

    internal_filename = '' # e.g. '.svn' or '.hg'

    def __init__(self):
        self.workingdir = os.getcwd()

    def get_setup_py_version(self):
        if os.path.exists('setup.py'):
            # First run egg_info, as that may get rid of some warnings
            # that otherwise end up in the extracted version, like
            # UserWarnings.
            ignore = getoutput('%s setup.py egg_info' % sys.executable)
            version = getoutput('%s setup.py --version' % sys.executable)
            return zest.releaser.utils.strip_version(version)

    def get_setup_py_name(self):
        if os.path.exists('setup.py'):
            # First run egg_info, as that may get rid of some warnings
            # that otherwise end up in the extracted name, like
            # UserWarnings.
            ignore = getoutput('%s setup.py egg_info' % sys.executable)
            return getoutput('%s setup.py --name' % sys.executable)

    def get_version_txt_version(self):
        version_file = self.filefind('version.txt')
        if version_file:
            f = open(version_file, 'r')
            version = f.read()
            return zest.releaser.utils.strip_version(version)

    def filefind(self, name):
        """Return first found file matching name (case-insensitive).

        Some packages have docs/HISTORY.txt and
        package/name/HISTORY.txt.  We make sure we only return the one
        in the docs directory if no other can be found.
        """
        for dirpath, dirnames, filenames in os.walk('.'):
            fname = self.internal_filename
            if fname in dirpath:
                # We are inside a version controlled directory.
                continue
            if fname not in dirnames:
                # This directory is not handled by version control.
                # Example: run prerelease in
                # https://svn.plone.org/svn/collective/feedfeeder/trunk
                # which is a buildout, so it has a parts directory.
                continue
            if 'docs' in dirnames:
                # Walk through the docs directory last, so we find
                # e.g. zest/releaser/HISTORY.txt before we find
                # docs/HISTORY.txt.
                dirnames.append(dirnames.pop(dirnames.index('docs')))
            for filename in filenames:
                if filename.lower() == name.lower():
                    fullpath = os.path.join(dirpath, filename)
                    logger.debug("Found %s", fullpath)
                    return fullpath

    def history_file(self):
        """Return history file location.
        """
        for name in ['HISTORY.txt', 'CHANGES.txt']:
            history = self.filefind(name)
            if history:
                return history

    def tag_exists(self, version):
        """Check if a tag has already been created with the name of the
        version.
        """
        for tag in self.available_tags():
            if tag == version:
                return True
        return False

    def _extract_version(self):
        """Extract the version from setup.py or version.txt.

        If there is a setup.py and it gives back a version that differs
        from version.txt then this version.txt is not the one we should
        use.  This can happen in packages like ZopeSkel that have one or
        more version.txt files that have nothing to do with the version of
        the package itself.

        So when in doubt: use setup.py.
        """
        return self.get_setup_py_version() or self.get_version_txt_version()

    def _update_version(self, version):
        """Find out where to change the version and change it.

        There are two places where the version can be defined. The first one is
        some version.txt that gets read by setup.py. The second is directly in
        setup.py.
        """
        current = self._extract_version()
        versionfile = self.filefind('version.txt')
        if versionfile:
            # We have a version.txt file but does it match the setup.py
            # version (if any)?
            setup_version = self.get_setup_py_version()
            if not setup_version or (setup_version ==
                                     self.get_version_txt_version()):
                open(versionfile, 'w').write(version + '\n')
                logger.info("Changed %s to %r", versionfile, version)
                return
        good_version = "version = '%s'" % version
        pattern = re.compile(r"""
        version\W*=\W*   # 'version =  ' with possible whitespace
        \d               # Some digit, start of version.
        """, re.VERBOSE)
        line_number = 0
        setup_lines = open('setup.py').read().split('\n')
        for line in setup_lines:
            match = pattern.search(line)
            if match:
                logger.debug("Matching version line found: %r", line)
                if line.startswith(' '):
                    # oh, probably '    version = 1.0,' line.
                    indentation = line.split('version')[0]
                    good_version = indentation + good_version + ','
                setup_lines[line_number] = good_version
                break
            line_number += 1
        contents = '\n'.join(setup_lines)
        open('setup.py', 'w').write(contents)
        logger.info("Set setup.py's version to %r", version)

    version = property(_extract_version, _update_version)

    #
    # Methods that need to be supplied by child classes
    #

    @property
    def name(self):
        "Name of the project under version control"
        raise NotImplementedError()

    def available_tags(self):
        """Return available tags."""
        raise NotImplementedError()

    def prepare_checkout_dir(self):
        """Return a tempoary checkout location. Create this directory first
        if necessary."""
        raise NotImplementedError()

    def tag_url(self, version):
        "URL to tag of version."
        raise NotImplementedError()

    def cmd_diff(self):
        "diff command"
        raise NotImplementedError()

    def cmd_commit(self, message):
        "commit command: should specify a verbose option if possible"
        raise NotImplementedError()

    def cmd_diff_last_commit_against_tag(self, version):
        """Return diffs between a tagged version and the last commit of
        the working copy.
        """
        raise NotImplementedError()

    def cmd_create_tag(self, version):
        "Create a tag from a version name."
        raise NotImplementedError()
