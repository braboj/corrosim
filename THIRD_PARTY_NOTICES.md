# Third-party notices

corrosim itself is MIT-licensed (see [LICENSE](LICENSE)). The published QM
container image (`ghcr.io/braboj/corrosim`) additionally redistributes the
third-party Python packages below, each under its own license. This file
records the attribution required for that redistribution; it is copied into the
image at `/licenses/THIRD_PARTY_NOTICES.md`.

Every component is redistributed unmodified, installed as a separate Python
package via pip. Each installed package keeps its full license text and
copyright in its own `*.dist-info/` metadata inside the image (under the Python
`site-packages` directory); the entries here summarise the obligation and point
to the authoritative upstream source.

## Weak-copyleft (LGPL) components

These two carry an explicit attribution obligation on redistribution. Each is
an unmodified, separately installed package that corrosim imports at runtime
rather than links statically, so a user may replace it with a modified build
without rebuilding corrosim, as the LGPL requires.

### ASE (Atomic Simulation Environment)

- License: GNU Lesser General Public License, version 2.1 or later
  (LGPL-2.1-or-later)
- Copyright: the ASE developers
- Source: https://gitlab.com/ase/ase
- License text: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html and in
  the package `dist-info` inside the image

### tblite

- License: GNU Lesser General Public License, version 3.0 or later
  (LGPL-3.0-or-later)
- Copyright: the tblite contributors
- Source: https://github.com/tblite/tblite
- License text: https://www.gnu.org/licenses/lgpl-3.0.html (with the base
  https://www.gnu.org/licenses/gpl-3.0.html) and in the package `dist-info`
  inside the image

## Permissive components

Also redistributed in the image, under permissive terms that require
attribution only:

| Package | License | Source |
| --- | --- | --- |
| numpy | BSD-3-Clause | https://github.com/numpy/numpy |
| pandas | BSD-3-Clause | https://github.com/pandas-dev/pandas |
| RDKit | BSD-3-Clause | https://github.com/rdkit/rdkit |
| matplotlib | Matplotlib License (BSD-style, PSF-based) | https://github.com/matplotlib/matplotlib |
| scipy | BSD-3-Clause | https://github.com/scipy/scipy |
| scikit-image | BSD-3-Clause | https://github.com/scikit-image/scikit-image |
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |
| PySCF | Apache-2.0 | https://github.com/pyscf/pyscf |
| geomeTRIC | BSD-3-Clause | https://github.com/leeping/geomeTRIC |
| python-docx | MIT | https://github.com/python-openxml/python-docx |

The image is built with the `[qm,dev]` extras, so it also contains the dev
toolchain (pytest, ruff, mypy, complexipy) and the transitive dependencies of
all of the above. Each ships under its own license, recorded in its
`*.dist-info/` metadata inside the image.
