def parseStationData(stationDataFile):
    from org.orekit.utils import IERSConventions
    from org.orekit.frames import FramesFactory
    itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)
    from org.orekit.models.earth import ReferenceEllipsoid
    wgs84ellipsoid = ReferenceEllipsoid.getWgs84(itrf)

    from org.orekit.bodies import GeodeticPoint
    from org.orekit.frames import TopocentricFrame
    from org.orekit.estimation.measurements import GroundStation
    from numpy import deg2rad

    import pandas as pd
    stationData = pd.Series()

    with open(stationDataFile) as f:
        line = ''
        while not line.startswith('+SITE/ID'):
            line = f.readline()
        line = f.readline() # Skipping +SITE/ID
        line = f.readline()  # Skipping column header

        while not line.startswith('-SITE/ID'):
            l = line[44:]
            lon_deg = float(l[0:3]) + float(l[3:6]) / 60.0 + float(l[6:11]) / 60.0 / 60.0
            lat_deg = float(l[12:15]) + float(l[15:18]) / 60.0 + float(l[18:23]) / 60.0 / 60.0
            alt_m = float(l[24:31])
            station_id = l[36:44]

            geodeticPoint = GeodeticPoint(float(deg2rad(lat_deg)), float(deg2rad(lon_deg)), alt_m)
            topocentricFrame = TopocentricFrame(wgs84ellipsoid, geodeticPoint, station_id)
            groundStation = GroundStation(topocentricFrame)

            stationData[station_id] = groundStation
            #stationData.append(groundStation)

            line = f.readline()

    return stationData

if __name__ == "__main__":
    parseStationData('SLRF2014_POS+VEL_2030.0_180504.snx')
