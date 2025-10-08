# Description

This repository provides examples for orbit determination based on laser ranging data, in the form of Jupyter Notebooks.

The open-source orbital dynamics library Orekit (https://www.orekit.org/) is used for all calculations, and in particular the Python wrapper developed by [@petrushy](https://github.com/petrushy): https://gitlab.orekit.org/orekit-labs/python-wrapper

# Installation
## Notes on Orekit versions

The Orekit example notebooks are based on Orekit 12.1.1 (previously 10.2 IIRC). The Orekit version is frozen in `pyproject.toml` to avoid breaking changes due to new Orekit major releases.

## Prerequisites

* Python 3.7+
* `uv` as package manager

## Create a venv and install dependencies

Now with `uv` it's easier:

```bash
uv sync
```

# Use

* Enter the venv: `source .venv/bin/activate`
* Start Jupyter Lab: `jupyter lab`
* Jupyter Lab should pop up in your browser at the URL http://localhost:8888

Or just open the notebook in VSCode and select the `.venv` as kernel.

# Updating data files
## Orekit data

## Laser ranging station coordinates
The station coordinates files (position&velocity) are updated from time to time. Check out for files named with the format `SLRF2020_POS+VEL_xxxxxx.snx` on ftp://cddis.nasa.gov/slr/products/resource/

The newest eccentricities file is always renamed `ecc_xyz.snx` and is available at ftp://cddis.gsfc.nasa.gov/slr/slrocc/ecc_xyz.snx
