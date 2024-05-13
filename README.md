# McSAS

Welcome to McSAS: a tool for analysis of SAS patterns. 
This tool can extract form-free size distributions from small-angle scattering data using the Monte-Carlo method described in:

Brian R. Pauw, Jan Skov Pedersen, Samuel Tardif, Masaki Takata, and Bo B. Iversen. *“Improvements and Considerations for Size Distribution Retrieval from Small-angle Scattering Data by Monte Carlo Methods.”* Journal of Applied Crystallography 46, no. 2 (February 14, 2013    ). [DOI:10.1107/S0021889813001295](http://dx.doi.org/10.1107/S0021889813001295).

The GUI and latest improvements are described in:
I. Breßler, B. R. Pauw, A. F. Thünemann, *"McSAS: A package for extracting quantitative form-free distributions"*. Journal of Applied Crystallography 48: 962-969, [DOI: 10.1107/S1600576715007347](http://dx.doi.org/10.1107/S1600576715007347)

## Features

Several form factors have been included in the package, including:

- Spheres

- Cylinders (spherically isotropic)

- Ellipsoids (spherically isotropic)

- Core-shell spheres and ellipsoids

- Gaussian chain

- Kholodenko worm

- Densely packed spheres (LMA-PY structure factor). 

## Standalone packages

Standalone packages are available in the [Releases](https://bitbucket.org/pkwasniew/mcsas/downloads) section of this page in the right pane. 
These are available for Mac OS X (tested on 10.6, 10.8 and 10.10), Windows and Linux. 
and should not require any additional software to be installed on the host computer. 
A quick start guide and example data is included in the "doc"-directory that comes with the distribution. 

## Run from source

### Requirements

To run McSAS from the source code repository using an existing Python environment,
there is a `requirements.txt` provided which contains the packages to be installed beforehand.

### Get a copy of the source code

Use the green "Code" button in the top left area of this page to download a copy of the latest source code tree.
Following this, McSAS can be started from a terminal window, as shown below:

1. Open a terminal window. Typically, it is opened in the current users home directory.
  You can change the current directory to `another/path` (which should exist) by entering
    ```
    cd another/path
    ```
2. Download a copy of the McSAS source code into the new directory `McSAS` using GIT:  
    (on Windows, [download & install GIT from here](https://git-scm.com/download/win))
    ```
    git clone https://github.com/BAMresearch/McSAS.git
    ```
### Linux/Ubuntu

1. Make sure, Python 3.11, *GIT* and *Qt5* is installed:
    ```
    sudo apt install python3.11 python3.11-venv git libqt5widgets5
    ```
2. Create a python virtual environment (venv) based on Python 3.11 for McSAS, in your home dir, for example:
    ```
    python3.11 -m venv --system-site-packages --symlinks ~/.py11env
    ```
3. Activate the new venv:
    ```
    source ~/.py11env/bin/activate
    ```
4. Clone the McSAS source tree to your local home directory:
    ```
    git clone https://github.com/BAMresearch/McSAS.git ~/mcsas
    ```
4. Install additional Python packages needed by McSAS:
    ```
    cd ~/mcsas
    pip install -r requirements.txt
    ```
5. Run McSAS from its `src` folder:
    ```
    cd ~/mcsas/src
    python -m mcsas
    ```

### Windows

1. Install the latest offline installer of the Qt5 series with defaults from here: https://www.qt.io/offline-installers
   That would be [Qt 5.12.12 for Windows](https://download.qt.io/archive/qt/5.12/5.12.12/qt-opensource-windows-x86-5.12.12.exe).

2. Install Python 3.11 (the latest supported for PySide2) via [Miniconda from here](https://docs.anaconda.com/free/miniconda/miniconda-other-installer-links/), [this is the installer package](https://repo.anaconda.com/miniconda/Miniconda3-py311_24.3.0-0-Windows-x86_64.exe).

3. After installing Miniconda, run _Anaconda Prompt_ from the Start Menu. Enter the McSAS project dir. Let's assume here, it's downloaded and extracted to `C:\McSAS`. Install the required packages with conda (make sure Qt was installed already for PySide2 to find the needed DLLs):
    ```
    cd /d C:\McSAS
    conda install -c conda-forge --file requirements.txt
    ```
4. After successful installation of the packages, from the same _Anaconda Prompt_, run McSAS from source dir with:
    ```
    cd /d C:\McSAS\src
    python -m mcsas
    ```
## Screenshots: ###

![McSAS20150111.png](https://bitbucket.org/repo/jkGXGq/images/2699194750-McSAS20150111.png)
![McSAS20150111Result.png](https://bitbucket.org/repo/jkGXGq/images/4000224154-McSAS20150111Result.png)
