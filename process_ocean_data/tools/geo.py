import re

import numpy as np
import requests
from bs4 import BeautifulSoup
from scipy.optimize import minimize


def dms2dd(s):
    """
    Convert latitude/longitude in string format to decimal degrees with Positive towards north/east.
    """
    # example: s = """0°51'56.29"S"""
    if s in [None, np.nan] or len(s) <= 1:
        dd = np.nan
    else:
        # Split String into components
        values_split = re.split(r'[°\'"\s]+', s)
        # Pre assign default value 0
        dd = float(0)

        if len(values_split) > 1:  # degree
            dd = float(values_split[0])
        if len(values_split) > 2:  # minutes
            dd = dd + float(values_split[1])/60
        if len(values_split) > 3:  # seconds
            dd = dd+float(values_split[2])/3600

        # direction
        if values_split[-1] in ('S', 'W'):
            dd = -dd    
        
    return dd


def get_mag_dec_from_nrcan(time, lat, lon):
    """
    Retrieve the magnetic declination for a specific site and time from the NRCAN website
    # Output the magnetic declination value and the rate of annual change East positive in degrees
    """
    # Get Date from datetime object
    date = time.strftime('%Y-%m-%d')
    
    # Set lat/long strings
    lat_str = str(abs(lat))
    lat_dir = str(lat/abs(lat))
    lon_str = str(abs(lon))
    lon_dir = str(lon/abs(lon))

    url = 'https://www.geomag.nrcan.gc.ca/calc/mdcal-r-en.php?date=' + date + \
          '&latitude=' + lat_str + '&latitude_direction=' + lat_dir + \
          '&longitude=' + lon_str + '&longitude_direction=' + lon_dir

    req = requests.get(url)
    soup = BeautifulSoup(req.content, 'html.parser')
    soup.find_all("p")

    # Get Magnetic Declination
    magnetic_string = re.findall(r"Magnetic declination: \d+\°[\s\d\.]+.\s\w+", soup.prettify())
    magnetic_declination = re.split(r"[:\°'']", magnetic_string[0])

    # Get Magnetic Annual Rate
    annual_rate_string = re.findall(r"Annual Change \(minutes\/year\)\:[\s\d\.]+\'\/y\s\w+",soup.prettify())
    annual_rate = re.split(r"\:|\'\/y", annual_rate_string[0])

    magnetic_declination_value = float(magnetic_declination[1])+float(magnetic_declination[2])/60
    annual_rate_value = float(annual_rate[1])/60

    if re.search('West', magnetic_declination[3]):
        magnetic_declination_value = -magnetic_declination_value

    if re.search('West', annual_rate[2]):
        annual_rate_value = -annual_rate_value
    
    return magnetic_declination_value, annual_rate_value


def trilateration_from_utm(distances_to_station, stations_coordinates):
    """
    #https://github.com/glucee/Multilateration/blob/master/Python/example.py
     Trilateration from UTM coordinates and distance from target.
    """
    def error(x, c, r):
        return sum([(np.linalg.norm(x - c[i]) - r[i]) ** 2 for i in range(len(c))])

    n_stations = len(stations_coordinates)
    distances_sum = sum(distances_to_station)
    
    # Compute weight vector for initial guess
    W = [((n_stations - 1) * distances_sum) / (distances_sum - w) for w in distances_to_station]
    
    # get initial guess of point location
    x0 = sum([W[i] * stations_coordinates[i] for i in range(n_stations)])
    
    # optimize distance from signal origin to border of spheres
    # TODO could probably extract the error which would be close the depth
    return minimize(error, x0, args=(stations_coordinates, distances_to_station), method='Nelder-Mead').x
