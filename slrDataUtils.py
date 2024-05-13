import requests
import json
from datetime import datetime
from datetime import timedelta
import pandas as pd
import os

from org.orekit.files.ilrs import CRDParser
from org.orekit.data import DataSource
from orekit.pyhelpers import absolutedate_to_datetime
from org.orekit.time import AbsoluteDate
from org.orekit.time import TimeScalesFactory

class SlrDlManager:
    c = 299792458  # m/s
    utc = TimeScalesFactory.getUTC()

    def __init__(self, username_edc: str, password_edc: str, url: str = 'https://edc.dgfi.tum.de/api/v1/') -> None:
        self.username_edc = username_edc
        self.password_edc = password_edc
        self.url = url

    def queryCpfData(self, cosparId, startDate):
        """
        Queries a list of CPF predictions for a given satellite and a given date. Usually there is one or two predictions
        every day, so this function will only look for predictions published at startDate.
        :param cosparId: str, COSPAR ID of the satellite
        :param startDate: datetime object, date where CPF prediction was published
        :return: pandas DataFrame object containing:
            - index: int, CPF id
            - columns: see section "Data query" for CPF data at https://edc.dgfi.tum.de/en/api/doc/
        """
        search_args = {}
        search_args['username'] = self.username_edc
        search_args['password'] = self.password_edc
        search_args['action'] = 'data-query'
        search_args['data_type'] = 'CPF'
        search_args['satellite'] = cosparId

        datasetList = pd.DataFrame()

        search_data = []
        while len(search_data) == 0:
            # Looping in case no CPF prediction is available on the desired day

            search_args['start_data_date'] = '{:%Y-%m-%d}%'.format(startDate)  # Data will start at midnight
            search_response = requests.post(self.url, data=search_args)

            if search_response.status_code == 200:
                search_data = json.loads(search_response.text)

                for observation in search_data:
                    startDataDate = datetime.strptime(observation['start_data_date'], '%Y-%m-%d %H:%M:%S')
                    endDataDate = datetime.strptime(observation['end_data_date'], '%Y-%m-%d %H:%M:%S')

                    leDataSet = pd.DataFrame.from_records(observation, index=[int(observation['id'])])
                    datasetList = pd.concat([datasetList, leDataSet])

            else:
                print(search_response.status_code)
                print(search_response.text)

            startDate = startDate - timedelta(days=1)

        datasetList.drop('id', axis=1, inplace=True)

        return datasetList

    def dlAndParseCpfData(self, datasetIdList, startDate, endDate):
        """
        NOTE: THIS PARSES THE CPF MANUALLY. INSTEAD, OREKIT SHOULD BE USED FOR THAT.
        Downloads and parses CPF prediction data. A CPF file usually contains one week of data. Using both startDate and
        endDate parameters, it is possible to truncate this data.
        :param datasetIdList: list of dataset ids to download.
        :param startDate: datetime object. Data prior to this date will be removed
        :param endDate: datetime object. Data after this date will be removed
        :return: pandas DataFrame containing:
            - index: datetime object of the data point, in UTC locale
            - columns 'x', 'y', and 'z': float, satellite position in ITRF frame in meters
        """
        dl_args = {}
        dl_args['username'] = self.username_edc
        dl_args['password'] = self.password_edc
        dl_args['action'] = 'data-download'
        dl_args['data_type'] = 'CPF'

        cpfDataFrame = pd.DataFrame(columns=['x', 'y', 'z'])

        for datasetId in datasetIdList:
            dl_args['id'] = str(datasetId)
            dl_response = requests.post(self.url, data=dl_args)

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
                    absolutedate = AbsoluteDate.createMJDDate(mjd_day, secondOfDay, self.utc)
                    currentdatetime = absolutedate_to_datetime(absolutedate)

                    if (currentdatetime >= startDate) and (currentdatetime <= endDate):
                        cpfDataFrame.loc[currentdatetime] = position_ecef

                    currentLine = data[i]
                    i += 1

            else:
                print(dl_response.status_code)
                print(dl_response.text)

        return cpfDataFrame

    def querySlrData(self, dataType, cosparId, startDate, endDate, station=None):
        """
        Queries a list of SLR ground station pass data
        :param dataType: str, NPT for normal point data or FRD for full-rate data
        :param cosparId: str, COSPAR ID of the satellite
        :param startDate: datetime object, start date to look for data
        :param endDate: datetime object, end date to look for data
        :param station: str, optional, for instance '78403501'
        :return: pandas DataFrame object, containing:
            - index: int, unique ID for the ground station pass
            - columns: see documentation for "Data query" in https://edc.dgfi.tum.de/en/api/doc/
        """
        # dataType: 'NPT' or 'FRD'
        search_args = {}
        search_args['username'] = self.username_edc
        search_args['password'] = self.password_edc
        search_args['action'] = 'data-query'
        search_args['data_type'] = dataType
        search_args['satellite'] = cosparId

        if station is not None:
            search_args['station'] = station

        datasetList = pd.DataFrame()

        search_args['start_data_date'] = '{:%Y}%'.format(startDate - timedelta(days=1))
        search_args['end_data_date'] = '{:%Y}%'.format(endDate + timedelta(days=1))

        search_response = requests.post(self.url, data=search_args)

        if search_response.status_code == 200:
            search_data = json.loads(search_response.text)

            for observation in search_data:
                startDataDate = datetime.strptime(observation['start_data_date'], '%Y-%m-%d %H:%M:%S')
                endDataDate = datetime.strptime(observation['end_data_date'], '%Y-%m-%d %H:%M:%S')
                #print('Observation Id: {}  -  Station: {}  -  Date: {}'.format(observation['id'],
                #                                                               observation['station'],
                #                                                               observation['end_data_date']))

                if (startDataDate >= startDate) and (
                        endDataDate <= endDate):  # Only taking the values within the date range

                    leDataSet = pd.DataFrame.from_records(observation, index=[int(observation['id'])])
                    datasetList = pd.concat([datasetList, leDataSet], ignore_index=False)

        else:
            print(search_response.status_code)
            print(search_response.text)

        if not datasetList.empty:
            datasetList.drop('id', axis=1, inplace=True)

        return datasetList


    def dlAndParseSlrData(self, dataType, datasetList, out_folder):
        """
        Download the CRD files specified by the user from the EDC API, parses it and return a Dataframe containing range and
        angles measurements

        :param dataType: str, NPT for normal point data or FRD for full-rate data
        :param datasetList: pandas Dataframe, returned by the querySlrData function
        :param out_folder: str, folder where to save the dataset
        :return: a pandas Dataframe containing:
            - index: datetime, receive time of the measurement
            - station-id: str, 8-digit id of the ground station
            - range: float, range in meters between ground station and satellite at bounce time
            - wavelength_microm: float, wavelength in micrometers. To be used for ionospheric delay model
            - pressure_mbar: float, pressure in millibars. To be used for ionospheric delay model
            - temperature_K: float, temperature in Kelvin. To be used for ionospheric delay model
            - humidity: float, humidity [0.0-1.0]. To be used for ionospheric delay model
        """
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)

        dl_args = {}
        dl_args['username'] = self.username_edc
        dl_args['password'] = self.password_edc
        dl_args['action'] = 'data-download'
        dl_args['data_type'] = dataType

        crd_parser = CRDParser()
        slr_dict = {}
        for datasetId, dataset in datasetList.iterrows():
            filename = os.path.join(out_folder, f'{datasetId}.{dataType.lower()}')
            if not os.path.isfile(filename):
                dl_args['id'] = str(datasetId)
                dl_response = requests.post(self.url, data=dl_args)

                if dl_response.status_code != 200:
                    return

                dl_data = dl_response.json()

                with open(filename, 'w') as f:
                    f.writelines([l + '\n' for l in dl_data])


            crd = crd_parser.parse(DataSource(filename))

            for data_block in crd.getDataBlocks():
                range_data = data_block.getRangeData()
                crd_header = data_block.getHeader()
                meteo_data = data_block.getMeteoData()
                conf_record = data_block.getConfigurationRecords()
                sys_record = conf_record.getSystemRecord()

                for range_meas in range_data:
                    timeOfFlight = range_meas.getTimeOfFlight()
                    meas_time = range_meas.getDate()

                    if range_meas.getEpochEvent() == 1:  # meas_time = bounce
                        receiveTime = meas_time.shiftedBy(timeOfFlight / 2)
                    elif range_meas.getEpochEvent() == 2:  # meas_time = ground transmit
                        receiveTime = meas_time.shiftedBy(timeOfFlight)
                    else:
                        print(f'Warning, unusual epoch indicator {range_meas.getEpochEvent()}')

                    r = self.c * timeOfFlight / 2

                    meteo_meas = meteo_data.getMeteo(meas_time)

                    slr_dict[meas_time] = [str(crd_header.getSystemIdentifier()),
                                        r, 1e6 * sys_record.getWavelength(),
                                        1e3 * meteo_meas.getPressure(), meteo_meas.getTemperature(), 1e-2*meteo_meas.getHumidity()]

        slrDataFrame = pd.DataFrame.from_dict(slr_dict,orient='index',columns=['station-id', 'range', 'wavelength_microm', 'pressure_mbar', 'temperature_K', 'humidity'])

        return slrDataFrame


    def write_cpf(self, cpf_df, cpf_filename, ephemeris_source, production_date, ephemeris_sequence, target_name, cospar_id,
                sic, norad_id, ephemeris_start_date, ephemeris_end_date, step_time, cpf_version=1, sub_daily_eph_seq=0):
        """
        DEPRECATED, THIS FUNCTION WRITES CPF DATA MANUALLY; INSTEAD, OREKIT SHOULD BE USED FOR THAT
        Writes satellite position data to a Consolidated prediction file.
        Reference: https://ilrs.cddis.eosdis.nasa.gov/docs/2006/cpf_1.01.pdf
        The function ignores leap seconds, i.e. it writes the UTC data directly and sets all leap seconds entries in the CPF file to zero

        :param cpf_df: DataFrame containing the date and position data. It must contain the following columns:
            - mjd_days: int, Modified Julian Days in UTC scale
            - seconds_of_day: float, seconds of day in UTC scale
            - x: float, satellite position in ITRF frame
            - y: float, satellite position in ITRF frame
            - z: float, satellite position in ITRF frame
        :param cpf_filename: str, filename where the data will be written
        :param ephemeris_source: str (e.g., "HON", "UTX"). Must be exactly 3 characters long
        :param production_date: datetime object. Date at which the orbit determination was performed
        :param ephemeris_sequence: int, incremented at each new orbit determination. Must be below 10000
        :param target_name: str, satellite name
        :param cospar_id: str, COSPAR ID
        :param sic: str, SIC
        :param norad_id: str, NORAD ID
        :param ephemeris_start_date: datetime
        :param ephemeris_end_date: datetime
        :param step_time: int
        :param cpf_version: int, 1 or 2. default is 1
        :param sub_daily_eph_seq: int, optional, only for CPF version 2. Must be below 99
        """

        assert(cpf_version in [1, 2])
        assert (len(ephemeris_source) == 3), 'Ephemeris source must be a string with exactly 3 characters'
        if (cpf_version == 1):
            assert ((ephemeris_sequence >= 5000) and ephemeris_sequence <= 10000), 'Ephemeris sequence must be between 5000 and 10000'
        elif (cpf_version == 2):
            assert ((ephemeris_sequence >= 0) and ephemeris_sequence <= 366), 'Ephemeris sequence must be between 0 and 366'
            assert ((sub_daily_eph_seq >= 0) and (sub_daily_eph_seq <= 99)), 'Sub-daily Ephemeris sequence must be between 0 and 99'

        with open(cpf_filename, 'w') as f:
            if (cpf_version == 1):
                f.write(
                    f'H1 CPF  1  {ephemeris_source} {production_date:%Y %m %d %H}  {ephemeris_sequence:04} {target_name:10}           \n')
                f.write(
                    f'H2  {cospar_id} {sic}    {norad_id} {ephemeris_start_date:%Y %m %d %H %M %S} {ephemeris_end_date:%Y %m %d %H %M %S} {step_time:5} 1 1  0 0 0\n')
            elif (cpf_version == 2):
                f.write(
                    f'H1 CPF  2 {ephemeris_source} {production_date:%Y %m %d %H}  {ephemeris_sequence:03} {sub_daily_eph_seq:02} {target_name:10}           \n')
                f.write(
                    f'H2  {cospar_id} {sic}    {norad_id} {ephemeris_start_date:%Y %m %d %H %M %S} {ephemeris_end_date:%Y %m %d %H %M %S} {step_time:5} 1 1  0 0 0  1\n')
            f.write('H9\n')

            for key, values in cpf_df.iterrows():
                f.write(
                    f"10 0 {values['mjd_days']} {values['seconds_of_day']:13.6f}  0  {values['x']:16.3f} {values['y']:16.3f} {values['z']:16.3f}\n")

            f.write('99')
