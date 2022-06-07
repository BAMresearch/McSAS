### Foreword ###
Welcome to McSAS: a tool for analysis of SAS patterns. 
This tool can extract form-free size distributions from small-angle scattering data using the Monte-Carlo method described in:

Brian R. Pauw, Jan Skov Pedersen, Samuel Tardif, Masaki Takata, and Bo B. Iversen. *“Improvements and Considerations for Size Distribution Retrieval from Small-angle Scattering Data by Monte Carlo Methods.”* Journal of Applied Crystallography 46, no. 2 (February 14, 2013    ). [DOI:10.1107/S0021889813001295](http://dx.doi.org/10.1107/S0021889813001295).

The GUI and latest improvements are described in:
I. Breßler, B. R. Pauw, A. F. Thünemann, *"McSAS: A package for extracting quantitative form-free distributions"*. Journal of Applied Crystallography 48: 962-969, [DOI: 10.1107/S1600576715007347](http://dx.doi.org/10.1107/S1600576715007347)

### Features ###

Several form factors have been included in the package, including:

- Spheres

- Cylinders (spherically isotropic)

- Ellipsoids (spherically isotropic)

- Core-shell spheres and ellipsoids

- Gaussian chain

- Kholodenko worm

- Densely packed spheres (LMA-PY structure factor). 

### Current status ###

The package should run on a Python 3 installation, for example an Anaconda environment.
Standalone packages are available for Windows, Linux and Mac OS X, make sure to get the latest release. 
A quick start guide and example data is included in the "doc"-directory that comes with the distribution. 

### Requirements ###

To run McSAS from the source code repository (i.e. using a Python interpreter), the following items are required:

- [Python 3](https://www.python.org/downloads/), with the following packages:

- [Numpy](http://www.scipy.org/scipylib/download.html) 

- [Scipy](http://www.scipy.org/scipylib/download.html) 

- [matplotlib](http://matplotlib.org/downloads.html) 

- [PySide2](https://pypi.org/project/PySide2/) 

### Installation on systems with a working Python distribution ###

For those unfamiliar with the Git versioning system, there is [helpful reading material provided by GitHub](https://github.com/git-guides)
and a somewhat easy to use graphical user interface [GitHub Desktop](https://desktop.github.com)
along with [extensive documentation about it](https://docs.github.com/en/desktop).
This is a GUI around the Git versioning system that simplifies the usage and allows you to get started quickly. 

Use the green "Code" button in the top left area of this page to download a copy of the latest source code tree.
Following this, McSAS can be started from a terminal window, as shown below:

### Cloning and Starting McSAS from a terminal window

Typically, the terminal window is opened in the current users home directory.
You can change the current directory to `another/path` (which should exist) by entering
```
cd another/path
```
To download a copy of the McSAS source code into the new directory `McSAS` enter
```
$ git clone https://github.com/BAMresearch/McSAS.git
```
To launch and start the McSAS GUI calling it like a Python module should be sufficient:
```
python3 -m McSAS
```

Alternatively, on Windows systems, double-clicking the "main.py" file should start McSAS with the primary Python interpreter as well.

### Standalone packages ###
Standalone packages are available in the [Releases](https://bitbucket.org/pkwasniew/mcsas/downloads) section of this page in the right pane. 
These are available for Mac OS X (tested on 10.6, 10.8 and 10.10), Windows and Linux. 
These do not require any additional software to be installed on the host computer. 

### Screenshots: ###
![McSAS20150111.png](https://bitbucket.org/repo/jkGXGq/images/2699194750-McSAS20150111.png)
![McSAS20150111Result.png](https://bitbucket.org/repo/jkGXGq/images/4000224154-McSAS20150111Result.png)
