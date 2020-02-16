This project contains some example data files useful that may be used
as an initial setup for the [Orekit library](http://www.orekit.org/).

In order to use these files, simply download the
[latest archive](https://gitlab.orekit.org/orekit/orekit-data/-/archive/master/orekit-data-master.zip)
and unzip it anywhere you want. Rename the `orekit-data-master` folder to
`orekit-data`, note the path of this folder and add the following lines at
the start of your program:

```java
File orekitData = new File("/path/to/the/folder/orekit-data");
DataProvidersManager manager = DataProvidersManager.getInstance();
manager.addProvider(new DirectoryCrawler(orekitData));
```

This zip file contains:

  * JPL DE 430 ephemerides from 1990 to 2069,
  * IERS Earth orientation parameters from 1973 to mid 2019
    with predicted data to late 2019 (both IAU-1980 and IAU-2000),
  * configuration data for ITRF versions used in regular IERS files,
  * UTC-TAI history from 1972 to end of 2019,
  * Marshall Solar Activity Future Estimation from 1999 to June 2019,
  * the Eigen 6S gravity field
  * the FES 2004 ocean tides model.

The provided archive is just a convenience, it is intended as a starting
point for Orekit setup. Users are responsible to update the files in
the unzipped folder to suit their needs as new data is published by IERS,
NASA... This is why we suggest to rename `orekit-data-master`
into `orekit-data` to show that the live data folder is decorrelated
from the initial master folder.

There is *NO* guarantee that this conveninence archive will be updated
or even provided in the future.
