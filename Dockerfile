# corrosim QM environment (Linux) ------------------------------------------
# The DFT (pyscf) and xTB (tblite) engines ship no Windows wheels and PySCF has
# no native-Windows support, so the quantum engines run here, in Linux. The host
# repo is bind-mounted over /work at runtime (see docker-compose.yml), so the
# editable install picks up your code edits without a rebuild.
#
#   docker compose build qm
#   docker compose run --rm qm pytest -q
#   docker compose run --rm qm python -m corrosim.runs.run_dft --engine pyscf \
#         --out-json dft_descriptors_ff.json --out-csv dft_descriptors_ff.csv
#
# Python 3.12: pyscf publishes manylinux wheels for it; tblite builds from the
# toolchain below if a wheel isn't used.
FROM python:3.12-slim

# Toolchain fallback for source builds (tblite/pyscf use wheels when available).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gfortran cmake ninja-build pkg-config \
        libopenblas-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# Copy only what's needed to resolve+install deps first (good layer caching).
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -e ".[qm,dev]"

# Resolve the package by its src/ location instead of the editable finder's
# build-time-baked absolute path, which goes stale when the layout moves (the
# src/ migration pointed the baked path at a now-nonexistent dir and every run
# needed a PYTHONPATH override). The repo is bind-mounted at /work, so /work/src
# is always the live package and the runtime import stays immune to that drift.
ENV PYTHONPATH=/work/src

# Fail the build loudly if the package or the engines do not import, so a broken
# image can never ship silently.
RUN python -c "import corrosim, pyscf, tblite"

# Default: confirm the quantum engines import.
CMD ["python", "-c", "import pyscf, tblite, corrosim; \
print('corrosim QM env OK | pyscf', pyscf.__version__, '| tblite ok')"]
