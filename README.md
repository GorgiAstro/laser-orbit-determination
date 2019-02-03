# Description

This repository provides examples for orbit determination based on laser ranging data, in the form of Jupyter Notebooks.

# Installation

Prerequisites:
* Anaconda or Miniconda

Install the conda environment. For this, you can either import the environment.yml file into Anaconda Navigator, or use the command line
 `conda env create -f environment.yml`

Optional: install Jupyter Lab extensions. I recommend:
* Table of contents: `jupyter labextension install @jupyterlab/toc`
* Variable inspect: `jupyter labextension install @lckr/jupyterlab_variableinspector`

# Use

* Enter conda environment: `source activate conda` (or start a terminal directly in the environment using Anaconda Navigator)
* Start Jupyter Lab: `jupyter lab`
* Jupyter Lab should pop up in your browser at the URL http://localhost:8888

# Issues

* It seems that the password input does not work in the latest versions of Firefox (as of 01.02.2019). However, it works in Chrome