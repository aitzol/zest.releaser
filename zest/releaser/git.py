from commands import getoutput
import logging
import tempfile
import os
import sys

from zest.releaser.vcs import BaseVersionControl

logger = logging.getLogger('git')


class Git(BaseVersionControl):
    """Command proxy for Git"""
    internal_filename = '.git'

    @property
    def name(self):
        package_name = self.get_setup_py_name()
        if package_name:
            return package_name
        # No setup.py? With git we can probably only fall back to the directory
        # name as there's no svn-url with a usable name in it.
        dir_name = os.path.basename(os.getcwd())
        return dir_name

    def available_tags(self):
        tag_info = getoutput('git tag')
        tags = [line for line in tag_info.split('\n') if line]
        logger.debug("Available tags: %r", tags)
        return tags

    def prepare_checkout_dir(self, prefix):
        temp = tempfile.mktemp(prefix=prefix)
        cmd = 'git clone %s %s' % (self.workingdir, temp)
        logger.debug(getoutput(cmd))
        return temp

    def tag_url(self, version):
        # this doesn't apply to Git, so we just return the
        # version name given ...
        return version

    def cmd_diff(self):
        return 'git diff'

    def cmd_commit(self, message):
        return 'git commit -a -m "%s"' % message

    def cmd_diff_last_commit_against_tag(self, version):
        return "git diff %s" % version

    def cmd_create_tag(self, version):
        return 'git tag %s -m "Tagging %s"' % (version, version)

    def cmd_checkout_from_tag(self, version, checkout_dir):
        if not (os.path.realpath(os.getcwd()) ==
                os.path.realpath(checkout_dir)):
            # Specific to git: we need to be in that directory for the command
            # to work.
            logger.warn("We haven't been chdir'ed to %s", checkout_dir)
            sys.exit(1)
        return 'git checkout %s' % version