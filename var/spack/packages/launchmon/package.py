##############################################################################
# Copyright (c) 2014, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Written by Matthew LeGendre, legendre1@llnl.gov, All rights reserved.
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
from spack import *

class Launchmon(Package):
    homepage = "http://sourceforge.net/projects/launchmon"
    url      = "http://sourceforge.net/code-snapshots/svn/l/la/launchmon/code/launchmon-code-481-branches-launchmon-1.0-release.zip"
    force_url = True
    list_url = "http://sourceforge.net/p/launchmon/code/HEAD/tree"

    #versions = {'1.0.0' : 'a0e5bfb7d82dc708d58bdbf93697886c'}
    versions = {'1.0.0' : '9d1184397d3081b94e2c0577c3c605e5'}
    patch('patch.lmon_install_dir', level=0)

    def install(self, spec, prefix):
        configure("--prefix=" + prefix)

        # TODO: remove once Jira SPACK-19 is fixed
        import shutil
        shutil.copy2('/usr/bin/libtool', 'libtool')

        make()
        make("install")