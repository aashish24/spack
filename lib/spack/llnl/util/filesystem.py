##############################################################################
# Copyright (c) 2013, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Written by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://scalability-llnl.github.io/spack
# Please also see the LICENSE file for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License (as published by
# the Free Software Foundation) version 2.1 dated February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
__all__ = ['set_install_permissions', 'install', 'expand_user', 'working_dir',
           'touch', 'touchp', 'mkdirp', 'force_remove', 'join_path', 'ancestor',
           'can_access', 'filter_file', 'change_sed_delimiter', 'is_exe']

import os
import sys
import re
import shutil
import stat
import errno
import getpass
from contextlib import contextmanager, closing
from tempfile import NamedTemporaryFile

import llnl.util.tty as tty
from spack.util.compression import ALLOWED_ARCHIVE_TYPES


def filter_file(regex, repl, *filenames, **kwargs):
    """Like sed, but uses python regular expressions.

       Filters every line of file through regex and replaces the file
       with a filtered version.  Preserves mode of filtered files.

       As with re.sub, ``repl`` can be either a string or a callable.
       If it is a callable, it is passed the match object and should
       return a suitable replacement string.  If it is a string, it
       can contain ``\1``, ``\2``, etc. to represent back-substitution
       as sed would allow.

       Keyword Options:
         string[=False]         If True, treat regex as a plain string.
         backup[=True]          Make a backup files suffixed with ~
         ignore_absent[=False]  Ignore any files that don't exist.
    """
    string = kwargs.get('string', False)
    backup = kwargs.get('backup', True)
    ignore_absent = kwargs.get('ignore_absent', False)

    # Allow strings to use \1, \2, etc. for replacement, like sed
    if not callable(repl):
        unescaped = repl.replace(r'\\', '\\')
        def replace_groups_with_groupid(m):
            def groupid_to_group(x):
                return m.group(int(x.group(1)))
            return re.sub(r'\\([1-9])', groupid_to_group, unescaped)
        repl = replace_groups_with_groupid

    if string:
        regex = re.escape(regex)

    for filename in filenames:
        backup = filename + "~"

        if ignore_absent and not os.path.exists(filename):
            continue

        shutil.copy(filename, backup)
        try:
            with closing(open(backup)) as infile:
                with closing(open(filename, 'w')) as outfile:
                    for line in infile:
                        foo = re.sub(regex, repl, line)
                        outfile.write(foo)
        except:
            # clean up the original file on failure.
            shutil.move(backup, filename)
            raise

        finally:
            if not backup:
                shutil.rmtree(backup, ignore_errors=True)


def change_sed_delimiter(old_delim, new_delim, *filenames):
    """Find all sed search/replace commands and change the delimiter.
       e.g., if the file contains seds that look like 's///', you can
       call change_sed_delimeter('/', '@', file) to change the
       delimiter to '@'.

       NOTE that this routine will fail if the delimiter is ' or ".
       Handling those is left for future work.
    """
    assert(len(old_delim) == 1)
    assert(len(new_delim) == 1)

    # TODO: handle these cases one day?
    assert(old_delim != '"')
    assert(old_delim != "'")
    assert(new_delim != '"')
    assert(new_delim != "'")

    whole_lines = "^s@([^@]*)@(.*)@[gIp]$"
    whole_lines = whole_lines.replace('@', old_delim)

    single_quoted = r"'s@((?:\\'|[^@'])*)@((?:\\'|[^'])*)@[gIp]?'"
    single_quoted = single_quoted.replace('@', old_delim)

    double_quoted = r'"s@((?:\\"|[^@"])*)@((?:\\"|[^"])*)@[gIp]?"'
    double_quoted = double_quoted.replace('@', old_delim)

    repl = r's@\1@\2@g'
    repl = repl.replace('@', new_delim)

    for f in filenames:
        filter_file(whole_lines, repl, f)
        filter_file(single_quoted, "'%s'" % repl, f)
        filter_file(double_quoted, '"%s"' % repl, f)


def set_install_permissions(path):
    """Set appropriate permissions on the installed file."""
    if os.path.isdir(path):
        os.chmod(path, 0755)
    else:
        os.chmod(path, 0644)


def install(src, dest):
    """Manually install a file to a particular location."""
    tty.info("Installing %s to %s" % (src, dest))
    shutil.copy(src, dest)
    set_install_permissions(dest)

    src_mode = os.stat(src).st_mode
    dest_mode = os.stat(dest).st_mode
    if src_mode | stat.S_IXUSR: dest_mode |= stat.S_IXUSR
    if src_mode | stat.S_IXGRP: dest_mode |= stat.S_IXGRP
    if src_mode | stat.S_IXOTH: dest_mode |= stat.S_IXOTH
    os.chmod(dest, dest_mode)


def is_exe(path):
    """True if path is an executable file."""
    return os.path.isfile(path) and os.access(path, os.X_OK)


def expand_user(path):
    """Find instances of '%u' in a path and replace with the current user's
       username."""
    username = getpass.getuser()
    if not username and '%u' in path:
        tty.die("Couldn't get username to complete path '%s'" % path)

    return path.replace('%u', username)


def mkdirp(*paths):
    """Creates a directory, as well as parent directories if needed."""
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)
        elif not os.path.isdir(path):
            raise OSError(errno.EEXIST, "File alredy exists", path)


def force_remove(*paths):
    """Remove files without printing errors.  Like rm -f, does NOT
       remove directories."""
    for path in paths:
        try:
            os.remove(path)
        except OSError, e:
            pass

@contextmanager
def working_dir(dirname, **kwargs):
    if kwargs.get('create', False):
        mkdirp(dirname)

    orig_dir = os.getcwd()
    os.chdir(dirname)
    yield
    os.chdir(orig_dir)


def touch(path):
    """Creates an empty file at the specified path."""
    with closing(open(path, 'a')) as file:
        os.utime(path, None)


def touchp(path):
    """Like touch, but creates any parent directories needed for the file."""
    mkdirp(os.path.dirname(path))
    touch(path)


def join_path(prefix, *args):
    path = str(prefix)
    for elt in args:
        path = os.path.join(path, str(elt))
    return path


def ancestor(dir, n=1):
    """Get the nth ancestor of a directory."""
    parent = os.path.abspath(dir)
    for i in range(n):
        parent = os.path.dirname(parent)
    return parent


def can_access(file_name):
    """True if we have read/write access to the file."""
    return os.access(file_name, os.R_OK|os.W_OK)
