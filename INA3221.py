#!/usr/bin/env python

# Driver library INA3221

from waiting import wait, TimeoutExpired
import smbus
import os
import csv
import datetime

class INA3221():

    # REGISTER ADDRESSES
    CONFIG =          (0x00)  # CONFIG REGISTER (R/W)
    SHUNTVOLTAGE =    [0x01, 0x03, 0x05]  # SHUNT VOLTAGE - SOLAR, BATTERY, LOAD (R)
    BUSVOLTAGE =      [0x02, 0x04, 0x06]  # BUS VOLTAGE - SOLAR, BATTERY, LOAD (R)
    MASKENABLE =      (0x0F)  # MASK/ENABLE REGISTER (R/W))

    # CONFIG REGISTER BITS
    RESET =           (0x8000)  # Reset Bit
    ENABLE_CHAN1 =    (0x4000)  # Enable the solar channel
    ENABLE_CHAN2 =    (0x2000)  # Enable the battery channel
    ENABLE_CHAN3 =    (0x1000)  # Enable the load channel
    AVG2 =            (0x0800)  # AVG 2
    AVG1 =            (0x0400)  # AVG 1
    AVG0 =            (0x0200)  # AVG 0
    VBUS_CT2 =        (0x0100)  # VBUS Conversion Time 2 
    VBUS_CT1 =        (0x0080)  # VBUS Conversion Time 1
    VBUS_CT0 =        (0x0040)  # VBUS Conversion Time 0
    VSH_CT2 =         (0x0020)  # Vshunt Conversion time 2
    SH_CT1 =          (0x0010)  # Vshunt Conversion time 1
    VSH_CT0 =         (0x0008)  # Vshunt Conversion time 0
    MODE_3 =          (0x0004)  # Operating Mode 3
    MODE_2 =          (0x0002)  # Operating Mode 2
    MODE_1 =          (0x0001)  # Operating Mode 1

    # A configuration setting with a) 16 measurements per reported average
    # on each channel while using the default b) conversion of 1.1 ms.  
    config_setting = (RESET |
                      ENABLE_CHAN1 |
                      ENABLE_CHAN2 |
                      ENABLE_CHAN3 |
                      AVG2 |
                      AVG1 |
                      AVG0 |
                      VBUS_CT2 |
#                      VBUS_CT1 |
#                      VBUS_CT0 |
                      VSH_CT2 |
#                      VSH_CT1 |
#                      VSH_CT0 |
#                      MODE_3 |
                      MODE_2 |
                      MODE_1)

    def __init__(self, address, twi=1, dataFile='/dev/null'):
        self._fetched = False
        self.dataFile = dataFile
        self._bus = smbus.SMBus(twi)
        self._address = address
        self.raw_shunt_voltage =       [0x0000, 0x0000, 0x0000]
        self.raw_bus_voltage =         [0x0000, 0x0000, 0x0000]
        self.processed_shunt_voltage = [0.0, 0.0, 0.0]
        self.processed_bus_voltage =   [0.0, 0.0, 0.0]
        self.load_voltage =            [0.0, 0.0, 0.0]
        self.current =                 [0.0, 0.0, 0.0]
        self.power =                   [0.0, 0.0, 0.0]

        self.coefficients =            [0.04, 0.008]  # shunt LSB (mV), bus LSB (V)
        self.shunt_resistor_value =     0.1  # default shunt resistor value of 0.1 Ohm

        # setup configuration register
        self._write_register(INA3221.CONFIG, INA3221.config_setting)

    def _write_register(self, register, data):
        '''reverse byte order first and then write 16 bit word'''
        val = ((data & 0xFFFF) >> 8) | ((data & 0x00FF) << 8)
        self._bus.write_word_data(self._address, register, val)

    def _read_register(self, register):
        '''read 16 bit word and then reverse byte order'''
        val = self._bus.read_word_data(self._address, register) & 0xFFFF
        data = ((val & 0xFFFF) >> 8) | ((val & 0x00FF) << 8)
        return data

    def _check_CVRF(self):
        '''Checks whether conversion ready flag bit is set.'''
        if self._read_register(INA3221.MASKENABLE) & 0x0001 == 0x0001:
            return True
        else:
            return False

    def fetch_shunt_bus_voltage_data(self):
        '''Wait for the CVRF bit in the MASK/ENABLE register to be set
        and if set then fetch the INA 3221 voltage values from each
        channel and store values in a list'''
        try:
            # Wait for conversion ready flag to be set True
            wait(self._check_CVRF, sleep_seconds=0.02, timeout_seconds=300.0)
            #  Get raw bus and shunt voltage from register address 1 to 6, the
            #  addresses that corresponds to both measurements on each channel
            for i, e in enumerate(INA3221.SHUNTVOLTAGE):
                self.raw_shunt_voltage[i] = self._read_register(e)
            for i, e in enumerate(INA3221.BUSVOLTAGE):
                self.raw_bus_voltage[i] = self._read_register(e)
            #  Make a note that there is now data to be had.
            self._fetched = True
            # Get date and time
            self.now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
        except TimeoutExpired:
            self._fetched = False
            print "Timeout expired - Data not fetched from device"
            return False

    def process_shunt_bus_voltage_data(self):
        '''Take raw data, format according to data sheet, and store
        the shunt and bus voltage as float in list'''
        for i, e in enumerate(self.raw_shunt_voltage):
            if (e & (1 << 15)) != 0:  # The MSB is set for negative numbers
                #  Take twos compliment and shift right to make 12 bit word
                #    according to data sheet
                twos_comp = ~((e - 0x0001) >> 3) & 0x0FFF
                self.processed_shunt_voltage[i] = -1 * twos_comp * self.coefficients[0]
            else:
                self.processed_shunt_voltage[i] = ((e >> 3) & 0x0FFF) * self.coefficients[0]
        #  Now for bus register
        for i, e in enumerate(self.raw_bus_voltage):
            if (e & (1 << 15)) != 0:  
                twos_comp = ~((e - 0x0001) >> 3) & 0x0FFF
                self.processed_bus_voltage[i] = -1 * twos_comp * self.coefficients[1]
            else:
                self.processed_bus_voltage[i] = ((e >> 3) & 0x0FFF) * self.coefficients[1]   
        
        # And now calculate the  values 
        for i, e in enumerate(self.load_voltage):
            self.load_voltage[i] = self.processed_bus_voltage[i] + self.processed_shunt_voltage[i]/1000.0
            self.current[i] = self.processed_shunt_voltage[i] / self.shunt_resistor_value
            self.power[i] = self.load_voltage[i] * self.current[i]     
    
    def record_data(self):
        if not os.path.exists(self.dataFile):
            with open(self.dataFile, 'w') as csvfile:
                datawriter = csv.writer(
                  csvfile,
                  quotechar=',',
                  quoting=csv.QUOTE_MINIMAL
                  )
                datawriter.writerow([
                  'Date',
                  
                  'SolarCell Voltage (V)',
                  'SolarCell Current (mA)',
                  'SolarCell Power (mA)',

                  'Battery Voltage (V)',
                  'Battery Current (mA)',
                  'Battery Power (mA)',

                  'Load Voltage (V)',
                  'Load Current (mA)',
                  'Load Power (mA)',
                  ])

        with open(self.dataFile, 'a+') as csvfile:
            datawriter = csv.writer(csvfile, quotechar=',', quoting=csv.QUOTE_MINIMAL)
            datawriter.writerow([
                self.now, 
                
                '%3.2f' % self.load_voltage[0],
                '%3.2f' %self.current[0],
                '%3.2f' %self.power[0],

                '%3.2f' %self.load_voltage[1],
                '%3.2f' %self.current[1],
                '%3.2f' %self.power[1],

                '%3.2f' %self.load_voltage[2],
                '%3.2f' %self.current[2],
                '%3.2f' %self.power[2],
                ])
                    
    def print_data(self):
        print "Solar Bus Voltage: %3.2f V " % self.processed_bus_voltage[0]
        print "Solar Shunt Voltage: %3.2f mV " % self.processed_shunt_voltage[0]
        print "Solar Load Voltage: %3.2f V" %  self.load_voltage[0]
        print "Solar Current:  %3.2f mA" % self.current[0]
        print "Solar Power:  %3.2f mW" % self.power[0]
        print

        print "Battery Bus Voltage:  %3.2f V " % self.processed_bus_voltage[1]
        print "Battery Shunt Voltage: %3.2f mV " % self.processed_shunt_voltage[1]
        print "Battery Load Voltage:  %3.2f V" %  self.load_voltage[1]
        print "Battery Current:  %3.2f mA" % self.current[1]
        print "Battery Power:  %3.2f mW" % self.power[1]
        print

        print "Load Bus Voltage:  %3.2f V " % self.processed_bus_voltage[2]
        print "Load Shunt Voltage: %3.2f mV " % self.processed_shunt_voltage[2]
        print "Load Load Voltage:  %3.2f V" %  self.load_voltage[2]
        print "Load Current:  %3.2f mA" % self.current[2]
        print "Load Power:  %3.2f mW" % self.power[2]
        print
