def epochStringToDatetime(epochString):
    from datetime import datetime, timedelta
    epochData = [int(d) for d in epochString.split(':')]
    if epochData[0] > 50: # 20th century
        epochYear = epochData[0] + 1900
    else:
        epochYear = epochData[0] + 2000
    referenceEpoch = datetime(epochYear, 1, 1) + timedelta(days=epochData[1] - 1) + timedelta(seconds=epochData[2])
    return referenceEpoch

def parseStationData(stationFile, stationEccFile, epoch):
    from org.orekit.utils import IERSConventions
    from org.orekit.frames import FramesFactory
    itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)
    from org.orekit.models.earth import ReferenceEllipsoid
    wgs84ellipsoid = ReferenceEllipsoid.getWgs84(itrf)

    from org.hipparchus.geometry.euclidean.threed import Vector3D
    from org.orekit.bodies import GeodeticPoint
    from org.orekit.frames import TopocentricFrame
    from org.orekit.estimation.measurements import GroundStation
    from numpy import deg2rad, rad2deg
    from orekit.pyhelpers import datetime_to_absolutedate

    import pandas as pd
    stationData = pd.DataFrame(columns=['Code', 'PT', 'Latitude', 'Longitude', 'Altitude', 'OrekitGroundStation'])
    stationxyz = pd.DataFrame(columns=['CODE', 'PT', 'TYPE', 'SOLN', 'REF_EPOCH',
                                   'UNIT', 'S', 'ESTIMATED_VALUE', 'STD_DEV'])

    # First run on the file to initialize the ground stations using the approximate lat/lon/alt data
    with open(stationFile) as f:
        line = ''
        while not line.startswith('+SITE/ID'):
            line = f.readline()
        line = f.readline()  # Skipping +SITE/ID
        line = f.readline()  # Skipping column header

        while not line.startswith('-SITE/ID'):
            stationCode = int(line[1:5])
            pt = line[7]
            l = line[44:]
            lon_deg = float(l[0:3]) + float(l[3:6]) / 60.0 + float(l[6:11]) / 60.0 / 60.0
            lat_deg = float(l[12:15]) + float(l[15:18]) / 60.0 + float(l[18:23]) / 60.0 / 60.0
            alt_m = float(l[24:31])
            station_id = l[36:44]

            geodeticPoint = GeodeticPoint(float(deg2rad(lat_deg)), float(deg2rad(lon_deg)), alt_m)
            topocentricFrame = TopocentricFrame(wgs84ellipsoid, geodeticPoint, str(station_id))
            groundStation = GroundStation(topocentricFrame)

            stationData.loc[station_id] = [stationCode, pt, lat_deg, lon_deg, alt_m, groundStation]

            line = f.readline()        

        # Parsing accurate ground station position from XYZ
        while not line.startswith('+SOLUTION/ESTIMATE'):
            line = f.readline()        

        line = f.readline()  # Skipping +SOLUTION/ESTIMATE
        line = f.readline()  # Skipping column header

        while not line.startswith('-SOLUTION/ESTIMATE'):
            index = int(line[1:6])
            lineType = line[7:11]
            code = int(line[14:18])
            pt = line[20:21]
            soln = int(line[22:26])
            refEpochStr = line[27:39]       
            refEpoch = epochStringToDatetime(refEpochStr)
            unit = line[40:44]
            s = int(line[45:46])
            estimatedValue = float(line[47:68])
            stdDev = float(line[69:80]) 

            stationxyz.loc[index] = [code, pt, lineType, soln, refEpoch, 
                                             unit, s, estimatedValue, stdDev]
            line = f.readline() 

    pivotTable = stationxyz.pivot_table(index=['CODE', 'PT'], 
                                        columns=['TYPE'], 
                                        values=['ESTIMATED_VALUE', 'STD_DEV'])
    stationxyz.set_index(['CODE', 'PT'], inplace = True)            
    # Reading the eccentricities data
    with open(stationEccFile) as f:
        for num, line in enumerate(f, 1):
            if '+SITE/ECCENTRICITY' in line:
                break
    lineNumberStart_ecc = num + 1  # skipping table header
    eccDataFrame = pd.read_csv(stationEccFile, engine='python',
                               names=['SITE', 'PT', 'SOLN', 'T', 'DATA_START', 'DATA_END', 'XYZ', 'X', 'Y', 'Z',
                                      'CDP-SOD'],
                               index_col=['SITE', 'PT'],
                               sep='\s+|\t+|\s+\t+|\t+\s+', skiprows=lineNumberStart_ecc, skipfooter=2)
    eccDataFrame['DATA_START'] = eccDataFrame['DATA_START'].apply(lambda x: epochStringToDatetime(x))
    eccDataFrame['DATA_END'] = eccDataFrame['DATA_END'].apply(lambda x: epochStringToDatetime(x))

    # A loop is needed here to create the Orekit objects
    for stationId, staData in stationData.iterrows():
        indexTuple = (staData['Code'], staData['PT'])
        refEpoch = stationxyz.loc[indexTuple]['REF_EPOCH'][0]
        yearsSinceEpoch = (epoch - refEpoch).days / 365.25

        pv = pivotTable.loc[indexTuple]['ESTIMATED_VALUE']
        x = float(pv['STAX'] + pv['VELX'] * yearsSinceEpoch)
        y = float(pv['STAY'] + pv['VELY'] * yearsSinceEpoch)
        z = float(pv['STAZ'] + pv['VELZ'] * yearsSinceEpoch)
        station_xyz_m = Vector3D(x, y, z)
        geodeticPoint = wgs84ellipsoid.transform(station_xyz_m, itrf, datetime_to_absolutedate(epoch))
        lon_deg = rad2deg(geodeticPoint.getLongitude())
        lat_deg = rad2deg(geodeticPoint.getLatitude())
        alt_m = geodeticPoint.getAltitude()
        topocentricFrame = TopocentricFrame(wgs84ellipsoid, geodeticPoint, str(indexTuple[0]))
        groundStation = GroundStation(topocentricFrame)
        stationData.loc[stationId] = [staData['Code'], staData['PT'], lat_deg, lon_deg, alt_m, groundStation]

    return stationData

def queryCpfData(username_edc, password_edc, url, cosparId, startDate):
    import requests
    import json
    search_args = {}
    search_args['username'] = username_edc
    search_args['password'] = password_edc
    search_args['action'] = 'data-query'
    search_args['data_type'] = 'CPF'
    search_args['satellite'] = cosparId

    from datetime import datetime

    import pandas as pd
    datasetList = pd.DataFrame()

    search_args['start_data_date'] = '{:%Y-%m-%d}%'.format(startDate) # Data will start at midnight

    search_response = requests.post(url, data=search_args)

    if search_response.status_code == 200:
        search_data = json.loads(search_response.text)

        for observation in search_data:
            startDataDate = datetime.strptime(observation['start_data_date'], '%Y-%m-%d %H:%M:%S')
            endDataDate = datetime.strptime(observation['end_data_date'], '%Y-%m-%d %H:%M:%S')

            leDataSet = pd.DataFrame.from_records(observation, index=[int(observation['id'])])
            datasetList = datasetList.append(leDataSet)

    else:
        print(search_response.status_code)
        print(search_response.text)

    datasetList.drop('id', axis=1, inplace=True)

    return datasetList

def dlAndParseCpfData(username_edc, password_edc, url, datasetList, startDate, endDate):
    # The data is truncated within the given time frame
    import requests
    import json
    from org.orekit.time import AbsoluteDate
    from org.orekit.time import TimeScalesFactory
    from orekit.pyhelpers import absolutedate_to_datetime
    utc = TimeScalesFactory.getUTC()

    dl_args = {}
    dl_args['username'] = username_edc
    dl_args['password'] = password_edc
    dl_args['action'] = 'data-download'
    dl_args['data_type'] = 'CPF'

    import pandas as pd
    cpfDataFrame = pd.DataFrame(columns=['x', 'y', 'z'])

    for datasetId, dataset in datasetList.iterrows():
        dl_args['id'] = str(datasetId)
        dl_response = requests.post(url, data=dl_args)

        if dl_response.status_code == 200:
            """ convert json string in python list """
            data = json.loads(dl_response.text)

            currentLine = ''
            i = 0
            n = len(data)

            while (not currentLine.startswith('10')) and i < n:  # Reading lines until the H4 header
                currentLine = data[i]
                i += 1

            while currentLine.startswith('10') and i < n:
                lineData = currentLine.split()
                mjd_day = int(lineData[2])
                secondOfDay = float(lineData[3])
                position_ecef = [float(lineData[5]), float(lineData[6]), float(lineData[7])]
                absolutedate = AbsoluteDate.createMJDDate(mjd_day, secondOfDay, utc)
                currentdatetime = absolutedate_to_datetime(absolutedate)

                if (currentdatetime >= startDate) and (currentdatetime <= endDate):
                    cpfDataFrame.loc[currentdatetime] = position_ecef

                currentLine = data[i]
                i += 1

        else:
            print(dl_response.status_code)
            print(dl_response.text)

    return cpfDataFrame

def querySlrData(username_edc, password_edc, url, dataType, cosparId, startDate, endDate):
    # dataType: 'NPT' or 'FRD'
    import requests
    import json
    search_args = {}
    search_args['username'] = username_edc
    search_args['password'] = password_edc
    search_args['action'] = 'data-query'
    search_args['data_type'] = dataType
    search_args['satellite'] = cosparId

    from datetime import datetime
    from datetime import timedelta

    import pandas as pd
    datasetList = pd.DataFrame()

    numberOfDays = (endDate - startDate).days

    for i in range(int(numberOfDays) + 1):  # Making a request for each day
        endDate_current = startDate + timedelta(days=i)
        search_args['end_data_date'] = '{:%Y-%m-%d}%'.format(endDate_current)

        search_response = requests.post(url, data=search_args)

        if search_response.status_code == 200:
            search_data = json.loads(search_response.text)

            for observation in search_data:
                startDataDate = datetime.strptime(observation['start_data_date'], '%Y-%m-%d %H:%M:%S')
                endDataDate = datetime.strptime(observation['end_data_date'], '%Y-%m-%d %H:%M:%S')

                if (startDataDate >= startDate) and (
                        endDataDate <= endDate):  # Only taking the values within the date range

                    leDataSet = pd.DataFrame.from_records(observation, index=[int(observation['id'])])
                    datasetList = datasetList.append(leDataSet)
                    # print('Observation Id: {}  -  Station: {}  -  Date: {}'.format(observation['id'],
                    #                                                               observation['station'],
                    #                                                               observation['end_data_date']))

        else:
            print(search_response.status_code)
            print(search_response.text)

    datasetList.drop('id', axis=1, inplace=True)
    return datasetList


def dlAndParseSlrData(username_edc, password_edc, url, dataType, datasetList):
    import requests
    import json
    from datetime import datetime
    from datetime import timedelta
    c = 299792458 # m/s

    dl_args = {}
    dl_args['username'] = username_edc
    dl_args['password'] = password_edc
    dl_args['action'] = 'data-download'
    dl_args['data_type'] = dataType

    import pandas as pd
    slrDataFrame = pd.DataFrame(columns=['station-id', 'range'])

    for datasetId, dataset in datasetList.iterrows():
        dl_args['id'] = str(datasetId)
        dl_response = requests.post(url, data=dl_args)

        if dl_response.status_code == 200:
            """ convert json string in python list """
            data = json.loads(dl_response.text)

            currentLine = ''
            i = 0
            n = len(data)

            while (not currentLine.lower().startswith('h4')) and i < n:  # Reading lines until the H4 header
                currentLine = data[i]
                i += 1

            lineData = currentLine.split()  # Reading day in H4 header
            y = int(lineData[2])
            m = int(lineData[3])
            d = int(lineData[4])
            measurementDay = datetime(y, m, d)

            while (not (currentLine.startswith('11') or currentLine.startswith('10'))) and i < n:  # Reading lines until the start of normal point data
                currentLine = data[i]
                i += 1

            while (currentLine.startswith('11') or currentLine.startswith('10'))\
                    and i < n:  # Reading until the end of normal point data
                lineData = currentLine.split()
                timeOfDay = float(lineData[1])
                timeOfFlight = float(lineData[2])
                timestampType = int(lineData[4])

                r = c * timeOfFlight / 2

                if timestampType == 1:
                    transmitTime = measurementDay + timedelta(seconds=(timeOfDay - timeOfFlight / 2))
                else:
                    transmitTime = measurementDay + timedelta(seconds=timeOfDay)

                bounceTime = transmitTime + timedelta(seconds=timeOfFlight / 2)
                receiveTime = bounceTime + timedelta(seconds=timeOfFlight / 2)

                #print('Transmit time: {}, receive time: {}'.format(transmitTime, receiveTime))
                #print('Time of flight: {} milliseconds, satellite range: {} kilometers'.format(timeOfFlight*1000, r/1000))
                #print('')
                slrDataFrame.loc[receiveTime] = [dataset['station'], r]

                currentLine = data[i]
                i += 1

        else:
            print(dl_response.status_code)
            print(dl_response.text)

    return slrDataFrame

def orekitPV2dataframe(PV, currentDateTime):
    import pandas as pd
    pos = PV.getPosition()
    vel = PV.getVelocity()
    data = {'x': pos.getX(), 'y': pos.getY(), 'z': pos.getZ(),
            'vx': vel.getX(), 'vy': vel.getY(), 'vz': vel.getZ()}
    return pd.DataFrame(data, index=[currentDateTime])