# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`camsrv` is a Python package providing web-based control and monitoring infrastructure for MMTO (Multiple Mirror Telescope Observatory) camera systems, including wavefront sensors, mount/rotator alignment cameras, and a simulator. Each camera has its own Tornado web server inheriting from a base class.

## Common Commands

```bash
# Install in development mode
pip install -e .
pip install -e .[test]       # With test dependencies
pip install -e .[docs]       # With documentation dependencies

# Run tests
pytest camsrv/tests docs

# Run a single test
pytest camsrv/tests/test_apps.py::TestSimSrv::test_homepage

# Code style (135 char max line length)
flake8 camsrv --count --max-line-length=135

# Via tox
tox -e codestyle
tox -e py312-test-cov
tox -e build_docs

# Start servers (after install)
simcam    # Simulator camera (port 8788)
f9wfs     # F/9 wavefront sensor (port 8787)
f5wfs     # F/5 wavefront sensor (port 8989, dev: 8988)
matcam    # Mount alignment camera (port 8786)
ratcam    # Rotator alignment camera (port 8789)
```

## Architecture

Each camera server is a subclass of `CAMsrv` (defined in `camsrv/camsrv.py`), which is a `tornado.web.Application`. The inheritance pattern:

```
CAMsrv (base Tornado app)
├── SimCam (INDI SimCam, inline in camsrv.py)
├── F9WFSsrv (f9wfs.py) — INDI-based F/9 WFS
├── F5WFSsrv (f5wfs.py) — INDI + async MSG protocol
├── MATsrv (matcam.py) — SBIG CCD, INDI
└── RATsrv (ratcam.py) — SBIG ST-I, INDI
```

**Web layer**: Tornado request handlers (REST + WebSocket). HTML served from `camsrv/web_resources/templates/`. Static assets in `camsrv/web_resources/` (Bootstrap, JS9 image viewer).

**Camera communication**:
- Most cameras use INDI protocol via `indiclient` (MMTObservatory/indiclient on GitHub)
- F/5 WFS also has an MSG-protocol interface in `f5wfs_camera.py` using `saomsg`
- `pyINDI` (MMTObservatory/pyINDI) used for Ekos/scheduler integration

**MMTO system integration** (`header.py`):
- FITS headers populated from MMTO API (`http://api.mmto.arizona.edu/APIv1`)
- Telescope state queried from Redis (`ops2.mmto.arizona.edu`)

### Key Files

| File | Purpose |
|------|---------|
| `camsrv/camsrv.py` | Base `CAMsrv` Tornado app; shared handlers (Home, Exposure, Status, Disconnect) |
| `camsrv/f5wfs.py` | F/5 WFS server; async INDI communication, driver restart |
| `camsrv/f5wfs_camera.py` | F/5 camera MSG protocol client; enums for camera state |
| `camsrv/f5wfs_hardware.py` | F/5 hardware interface |
| `camsrv/f9wfs.py` | F/9 WFS server |
| `camsrv/matcam.py` | Mount alignment camera server |
| `camsrv/ratcam.py` | Rotator alignment camera server |
| `camsrv/header.py` | FITS header population from MMTO API + Redis |
| `camsrv/data/` | FITS detector mask files (f5_mask.fits, f9_mask.fits) |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `WFSDEV` | unset | Enable development mode (local imports) |
| `INDIF5WFSHOST` | f5wfs.mmto.arizona.edu | F/5 INDI server host |
| `INDIF5WFSPORT` | 7625 | F/5 INDI server port |
| `MATCAMROOT` | /mmt/matcam/latest | MATCam image output directory |

## Code Style

- Line length: 135 characters (configured in tox.ini)
- Formatter: black (used as baseline, run before commits)
- Python 3.12+ required
- Version managed via setuptools_scm

## Testing

Tests use `tornado.testing.AsyncHTTPTestCase` with `@gen_test` decorators. Each camera type has a test class in `camsrv/tests/test_apps.py`. Tests start actual Tornado apps and hit HTTP endpoints.

Docker Compose configs available for dev/prod deployment (`docker-compose*.yml`).
