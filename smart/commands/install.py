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
from smart.transaction import Transaction, PolicyInstall, sortUpgrades
from smart.transaction import INSTALL, REINSTALL
from smart.option import OptionParser
from smart.cache import Package
from smart import *
import string
import re
import os

USAGE=_("smart install [options] package ...")

DESCRIPTION=_("""
This command will install one or more packages in the
system. If a new version of an already installed package
is available, it will be selected for installation.
""")

EXAMPLES=_("""
smart install pkgname
smart install '*kgna*'
smart install pkgname-1.0
smart install pkgname-1.0-1
smart install pkgname1 pkgname2
smart install ./somepackage.file
smart install http://some.url/some/path/somepackage.file
""")

def option_parser():
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.add_option("--attempt", action="store_true",
                      help=_("attempt to install packages, ignore failures"))
    parser.add_option("--stepped", action="store_true",
                      help=_("split operation in steps"))
    parser.add_option("--urls", action="store_true",
                      help=_("dump needed urls and don't commit operation"))
    parser.add_option("--metalink", action="store_true",
                      help=_("dump metalink xml and don't commit operation"))
    parser.add_option("--download", action="store_true",
                      help=_("download packages and don't commit operation"))
    parser.add_option("--explain", action="store_true",
                      help=_("include additional information about changes,"
                             "when possible"))
    parser.add_option("-y", "--yes", action="store_true",
                      help=_("do not ask for confirmation"))
    parser.add_option("--dump", action="store_true",
                      help=_("dump package names and versions to stderr but "
                             "don't commit operation"))
    return parser

def parse_options(argv):
    parser = option_parser()
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):
 
    # Argument check
    if not opts.args:
        raise Error, _("no package(s) given")

    if opts.attempt:
	sysconf.set("attempt-install", True, soft=True)

    if opts.explain:
        sysconf.set("explain-changesets", True, soft=True)

    urls = []
    for arg in opts.args[:]:
        if (os.path.isfile(arg) and
            '/' in arg or ctrl.checkPackageFile(arg)):
            ctrl.addFileChannel(arg)
            opts.args.remove(arg)
        elif ":/" in arg:
            urls.append(arg)
    if urls:
        succ, fail = ctrl.downloadURLs(urls, _("packages"),
                                       targetdir=os.getcwd())
        if fail:
            raise Error, _("Failed to download packages:\n") + \
                         "\n".join(["    %s: %s" % (url, fail[url])
                                    for url in fail])
        for url, file in succ.items():
            ctrl.addFileChannel(file)
            opts.args.remove(url)
    if sysconf.get("auto-update"):
        from smart.commands import update
        updateopts = update.parse_options([])
        update.main(ctrl, updateopts)
    else:
        ctrl.reloadChannels()
    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyInstall)
    for channel in ctrl.getFileChannels():
        for loader in channel.getLoaders():
            for pkg in loader.getPackages():
                if pkg.installed:
                    raise Error, _("%s is already installed") % pkg
                trans.enqueue(pkg, INSTALL)


    for arg in opts.args:

        ratio, results, suggestions = ctrl.search(arg)

        if not results:
            if suggestions:
                dct = {}
                for r, obj in suggestions:
                    if isinstance(obj, Package):
                        dct[obj] = True
                    else:
                        dct.update(dict.fromkeys(obj.packages, True))
                raise Error, _("'%s' matches no packages. "
                               "Suggestions:\n%s") % \
                             (arg, "\n".join(["    "+str(x) for x in dct]))
            else:
                raise Error, _("'%s' matches no packages") % arg

        pkgs = []

        for obj in results:
            if isinstance(obj, Package):
                pkgs.append(obj)

        if not pkgs:
            installed = False
            names = {}
            for obj in results:
                for pkg in obj.packages:
                    if pkg.installed:
                        iface.info(_("%s (for %s) is already installed")
                                      % (pkg, arg))
                        installed = True
                        break
                    else:
                        pkgs.append(pkg)
                        names[pkg.name] = True
                else:
                    continue
                break
            if installed:
                continue
            if len(names) == 2 and sysconf.get("rpm-strict-multilib"):
                from smart.backends.rpm.rpmver import splitarch
                # two packages with the same version but different arch, pick best
                if splitarch(pkgs[0].version)[0] == splitarch(pkgs[1].version)[0]:
                    pkg = max(pkgs[0], pkgs[1])
                    names.pop(pkg.name)
                    pkgs.remove(pkg)
            if len(names) > 1:
                raise Error, _("There are multiple matches for '%s':\n%s") % \
                              (arg, "\n".join(["    "+str(x) for x in pkgs]))

        if len(pkgs) > 1:
            sortUpgrades(pkgs)

        names = {}
        for pkg in pkgs:
            names.setdefault(pkg.name, []).append(pkg)
        for name in names:
            pkg = names[name][0]
            if pkg.installed:
                iface.info(_("%s is already installed") % pkg)
            else:
                trans.enqueue(pkg, INSTALL)

    iface.showStatus(_("Computing transaction..."))
    trans.run()
    iface.hideStatus()
    if trans:
        confirm = not opts.yes
        if opts.urls:
            ctrl.dumpTransactionURLs(trans)
        elif opts.metalink:
            ctrl.dumpTransactionMetalink(trans)
        elif opts.dump:
            ctrl.dumpTransactionPackages(trans, install=True)
        elif opts.download:
            ctrl.downloadTransaction(trans, confirm=confirm)
        elif opts.stepped:
            ctrl.commitTransactionStepped(trans, confirm=confirm)
        else:
            ctrl.commitTransaction(trans, confirm=confirm)

# vim:ts=4:sw=4:et
