import numpy as _n
import serial

class arduino_api():
    """
    Commands-only object for interacting with an Arduino
    temperature controller.
    
    Parameters
    ----------
    port='COM3' : str
        Name of the port to connect to.
        
    address=1 : int
        Address of the instrument. Can be 0-255, and must match the instrument
        setting.
        
    baudrate=9600 : int
        Baud rate of the connection. Must match the instrument setting.
        
    timeout=2000 : number
        How long to wait for responses before giving up (ms). Must be >300 for this instrument.
        
    temperature_limit=450 : float
        Upper limit on the temperature setpoint (C).
    """
    def __init__(self, port='COM3', address=0, baudrate=9600, timeout=50, temperature_limit=500):

        self._temperature_limit = temperature_limit        

        # Check for installed libraries
        if  not serial:
            _s._warn('You need to install pyserial and to use the Arduino.')
            self.simulation_mode = True

        # Assume everything will work for now
        else: self.simulation_mode = False

        # If the port is "Simulation"
        if port=='Simulation': self.simulation_mode = True
        
        self.simulation_setpoint = 24.5

        # If we have all the libraries, try connecting.
        if not self.simulation_mode:
            try:
                # Create the instrument and ensure the settings are correct.
                self.serial = serial.Serial(port=port,baudrate=baudrate, timeout=timeout)

                # Simulation mode flag
                self.simulation_mode = False

            # Something went wrong. Go into simulation mode.
            except Exception as e:
                print('Could not open connection to "'+port+':'+str(address)+'" at baudrate '+str(baudrate)+'. Entering simulation mode.')
                print(e)
                self.modbus = None
                self.simulation_mode = True
    
    def read_all(self):
        return self.serial.read_all().decode()
    
    def write(self, msg):
        return self.serial.write(msg.encode())

    def disconnect(self):
        """
        Disconnects.
        """
        if not self.simulation_mode: self.serial.close()
