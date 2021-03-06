#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
import fcntl
import os
import sys

class PathLocks(object):
    
    def __init__(self, force=True):
        self._lock = {}
        self._force = bool(force)

    def getForce(self):
        return self._force

    def setForce(self, flag):
        self._force = flag

    def __del__(self):
        # fcntl module may be destructed before we are.
        if fcntl: self.unlockAll()

    def unlockAll(self):
        for path in self._lock:
            fd = self._lock[path]
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        self._lock.clear()

    def unlock(self, path):
        result = self._force
        fd = self._lock.get(path)
        if fd is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            del self._lock[path]
            result = True
        return result

    def lock(self, path, exclusive=False, block=False):
        result = self._force
        fd = self._lock.get(path)
        if fd is None:
            solaris = (sys.platform == "sunos5")
            if solaris and exclusive:
                if os.path.isdir(path) or path.endswith('/'):
                    file = os.path.join(path, ".lck")
                    if not os.path.exists(file):
                        fd = os.open(file, os.O_RDWR | os.O_CREAT)
                    else:
                        fd = os.open(file, os.O_RDWR)
                else:
                    fd = os.open(path, os.O_RDWR)
            elif solaris and not block:
                if os.path.isdir(path) or path.endswith('/'):
                    file = os.path.join(path, ".lck")
                    try:
                        fd = os.open(file, os.O_RDWR | os.O_CREAT)
                    except OSError:
                        fd = os.open(path, os.O_RDONLY )
                else:
                    fd = os.open(path, os.O_RDONLY)
            else:
                fd = os.open(path, os.O_RDONLY)
            self._lock[path] = fd
            flags = fcntl.fcntl(fd, fcntl.F_GETFD, 0)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(fd, fcntl.F_SETFD, flags)
        if exclusive:
            flags = fcntl.LOCK_EX
        else:
            flags = fcntl.LOCK_SH
        if not block:
            flags |= fcntl.LOCK_NB
        try:
            fcntl.flock(fd, flags)
            result = True
        except IOError, e:
            pass
        return result
