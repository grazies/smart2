from epm.transaction import INSTALL, REMOVE
from epm import *

class Committer(object):

    def __init__(self):
        self._fetcher = None
        self._progress = None

    def setFetcher(self, fetcher):
        self._fetcher = fetcher

    def getFetcher(self):
        return self._fetcher

    def setProgress(self, prog):
        self._progress = prog

    def getProgress(self):
        return self._progress

    def acquire(self, trans):
        set = trans.getChangeSet().getSet()
        pkgurl = {}
        for pkg in set:
            if set[pkg] is REMOVE:
                continue
            loader = [x for x in pkg.loaderinfo if not x.getInstalled()][0]
            info = loader.getInfo(pkg)
            pkgurl[pkg] = info.getURL()
        acquired, failed = self._fetcher.get(pkgurl.values(),
                                             "packages")
        if failed:
            raise Error, "failed to download packages:\n" + \
                         "\n".join(["    "+url for url in failed])
        pkgpath = {}
        for pkg in set:
            if set[pkg] is REMOVE:
                continue
            pkgpath[pkg] = acquired[pkgurl[pkg]]
        return pkgpath

    def commit(self, trans, pkgpath):
        prog = self._progress
        prog.reset()
        pmmap = {}
        set = trans.getChangeSet().getSet()
        for pkg in set:
            pmclass = pkg.packagemanager
            if pmclass not in pmmap:
                pmmap[pmclass] = {pkg: set[pkg]}
            else:
                pmmap[pmclass][pkg] = set[pkg]
        for pmclass in pmmap:
            pm = pmclass()
            pm.setProgress(prog)
            pm.commit(pmmap[pmclass], pkgpath)

    def acquireAndCommit(self, trans):
        pkgpath = self.acquire(trans)
        self.commit(trans, pkgpath)

# vim:ts=4:sw=4:et
