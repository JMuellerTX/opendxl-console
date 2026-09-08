# About this directory

This is a download of the SmartClient LGPL SDK that was committed to the
repository in 2018 (commit `065a0d6`, "Added SmartClient source code"). Two
things about it are easy to get wrong, so they are written down here.

**It is not the source of the runtime this project ships.** The console
serves `dxlconsole/web/isomorphic/`, which is SmartClient
**v11.1p_2017-08-20**. This directory is **v11.1p_2018-06-28** — a build ten
months younger. Every module file differs, and the SDK even contains one
module the shipped tree does not. So this directory cannot be, and never
was, the "corresponding source" for what is distributed.

The corresponding source for the shipped, minified modules is shipped with
them: `dxlconsole/web/isomorphic/system/modules-debug/` is the unminified,
commented form, carries the same version string, and is part of the pip
package and the container image. See `NOTICE` in the repository root, which
also names the licence, the copyright holder and the download location, and
`LICENSE.LGPL-3.0.txt` / `LICENSE.GPL-3.0.txt` for the licence texts.

**`smartclientSDK/WEB-INF/` has been removed.** It held the SDK's embedded
Tomcat and the Java libraries for the server-side examples — 171 files,
about 70 MB, 75 JAR archives. None of it was ever distributed: it is
excluded by `.dockerignore` and appears in neither the sdist nor the wheel
(`setup.py` packages only `dxlconsole.*`). It was, however, the entire
source of this repository's vulnerability findings — 12 critical and 33
high, all of them, in `tomcat-embed-core` 8.5.32, `log4j` 1.2.17,
`commons-fileupload` 1.3.3 and their neighbours. Removing it costs nothing
and clears all of them.

What remains is the part the licence actually talks about: `source/` (the
LGPL-licensed SmartClient source), `isomorphic/`, the examples, the tools
and `license.html`. The removed files stay reachable in the git history at
`065a0d6` for anyone who needs them.
