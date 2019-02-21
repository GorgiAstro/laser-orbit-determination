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

            line = f.readline()

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
    from datetime import timedelta

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
    from datetime import datetime
    from datetime import timedelta
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

            # print(currentLine)

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

if __name__ == "__main__":
    parseStationData('SLRF2014_POS+VEL_2030.0_180504.snx')
