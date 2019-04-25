from datetime import datetime


class Ccsds:
    originator = ''
    object_name = ''
    object_id = 0
    sat_properties = {
         'mass': 0.0,
         'solar_rad_area': 0.0,
         'solar_rad_coeff': 0.0,
         'drag_area': 0.0,
         'drag_coeff': 0.0
    }

    def __init__(self, originator, object_name, object_id, sat_properties):
        """

        :param originator:
        :param object_name:
        :param object_id:
        :param sat_properties: dict containing at least:
            - mass: float, kg
            - solar_rad_area: float, area for radiation pressure in m2
            - solar_rad_coeff: float, radiation pressure coefficient
            - drag_area: float, area for drag in m2
            - drag_coeff: float, drag coefficient
        """
        self.originator = originator
        self.object_name = object_name
        self.object_id = object_id
        self.sat_properties = sat_properties

    def write_opm(self, filename, epoch, pos_array, vel_array, cov_matrix, center_name, frame_name):
        """
        Timescale is forced to UTC
        :param filename:
        :param epoch:
        :param pos_array:
        :param vel_array:
        :param cov_matrix:
        :param center_name:
        :param frame_name:
        :return:
        """

        epoch_str = f'{epoch:%Y-%m-%dT%H:%M:%S.%f}'
        pos_km = 1e-3 * pos_array
        vel_km_s = 1e-3 * vel_array

        with open(filename, 'w') as f:

            f.write('CCSDS_OPM_VERS = 2.0\n')
            f.write('\n')
            f.write(f'CREATION_DATE = {datetime.utcnow():%Y-%m-%dT%H:%M:%S}\n')
            f.write(f'ORIGINATOR = {self.originator}\n')
            f.write('\n')
            f.write(f'OBJECT_NAME = {self.object_name}\n')
            f.write(f'OBJECT_ID = {self.object_id}\n')
            f.write(f'CENTER_NAME = {center_name}\n')
            f.write(f'REF_FRAME = {frame_name}\n')
            f.write('TIME_SYSTEM = UTC\n')
            f.write('\n')
            f.write('COMMENT  Orbit determination based on SLR data\n')
            f.write('\n')

            f.write('COMMENT  State vector\n')
            f.write(f'EPOCH = {epoch_str[:-3]}\n')
            f.write(f'X = {pos_km[0]:.9f}  [km]\n')
            f.write(f'Y = {pos_km[1]:.9f}  [km]\n')
            f.write(f'Z = {pos_km[2]:.9f}  [km]\n')
            f.write(f'X_DOT = {vel_km_s[0]:.12f}  [km/s]\n')
            f.write(f'Y_DOT = {vel_km_s[1]:.12f}  [km/s]\n')
            f.write(f'Z_DOT = {vel_km_s[2]:.12f}  [km/s]\n')
            f.write('\n')

            f.write('COMMENT  Spacecraft parameters\n')
            f.write(f'MASS = {self.sat_properties["mass"]:.6f}  [kg]\n')
            f.write(f'SOLAR_RAD_AREA = {self.sat_properties["solar_rad_area"]:.6f}  [m**2]\n')
            f.write(f'SOLAR_RAD_COEFF = {self.sat_properties["solar_rad_coeff"]:.6f}\n')
            f.write(f'DRAG_AREA = {self.sat_properties["drag_area"]:.6f}  [m**2]\n')
            f.write(f'DRAG_COEFF = {self.sat_properties["drag_coeff"]:.6f}\n')
            f.write('\n')
