##
# Copyright 2012-2025 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
Support for MVAPICH2 as toolchain MPI library.

Authors:

* Stijn De Weirdt (Ghent University)
* Kenneth Hoste (Ghent University)
"""

from easybuild.toolchains.mpi.mpich2 import Mpich2


TC_CONSTANT_MVAPICH2 = "MVAPICH2"


class Mvapich2(Mpich2):
    """MVAPICH2 MPI class"""
    MPI_MODULE_NAME = ["MVAPICH2"]
    MPI_FAMILY = TC_CONSTANT_MVAPICH2

    MPI_LIBRARY_NAME = 'mpich'

    MPI_LINK_INFO_OPTION = '-link_info'
