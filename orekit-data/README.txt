This zip file contains some data files useful for
use with the orekit library (http://www.orekit.org/).

In order to use this file, simply unzip it anywhere you
want, note the path of the orekit-data folder that will
be created and add the following lines at the start of
your program:

  File orekitData = new File("/path/to/the/folder/orekit-data");
  DataProvidersManager manager = DataProvidersManager.getInstance();
  manager.addProvider(new DirectoryCrawler(orekitData));

This zip file contains JPL DE 430 ephemerides from 1990 to 2069,
IERS Earth orientation parameters from 1973 to March 2018 with
predicted date to mid 2018 (both IAU-1980 and IAU-2000), configuration
data for ITRF versions used in regular IERS files, UTC-TAI history
from 1972 to mid of 2018, Marshall Solar Activity Futur Estimation
from 1999 to May 2018, the Eigen 6S gravity field and the FES 2004
ocean tides model.
