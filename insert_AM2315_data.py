#!/usr/bin/env python3
#insert_AM2315_data.py
#

import pymysql as mdb
import logging
import sys
sys.path.append('/home/weather-station/libraries')
import am2315

# Setup logging
logging.basicConfig(filename='/home/weather-station/data-files/am2315_error.log',
  format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)


# Function for storing readings into MySQL
def insertDB(temperature,humidity):


  try:

    con = mdb.connect('localhost',
                      'weather_insert',
                      '##############',
                      'measurements');

    cursor = con.cursor()

    sql = "INSERT INTO am2315(temperature, humidity) \
    VALUES ('%s', '%s')" % \
    (temperature, humidity)
    cursor.execute(sql)
    sql = []
    con.commit()

    con.close()

  except mdb.Error as e:
    logger.error(e)



# Get readings from sensor and store them in MySQL
sensor = am2315.Sensor()
data =sensor.data()

temperature = data[1]
temperatureF = data[2]
humidity = data[0]


print(temperature, "  ", temperatureF, "   ", humidity)
insertDB(temperature,humidity)


