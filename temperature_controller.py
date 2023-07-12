import spinmob.egg   as _egg
import spinmob       as _s
import mcphysics     as _mc
import time          as _time
import os            as _os
import serial        as _serial

_g            = _egg.gui
_serial_tools = _mc.instruments._serial_tools

from serial.tools.list_ports import comports as _comports
from _arduino_api import arduino_api

# GUI settings
_s.settings['dark_theme_qt'] = True

# Print data to terminal for debugging
_debug = True


class serial_gui_base(_g.BaseObject):
    """
    Base class for creating a serial connection gui. Handles common controls.
    
    Parameters
    ----------
    api_class=None : class
        Class to use when connecting. For example, api_class=auber_syl53x2p_api would
        work. Note this is not an instance, but the class itself. An instance is
        created when you connect and stored in self.api.
        
    name='serial_gui' : str
        Unique name to give this instance, so that its settings will not
        collide with other egg objects.
        
    show=True : bool
        Whether to show the window after creating.
        
    block=False : bool
        Whether to block the console when showing the window.
        
    window_size=[1,1] : list
        Dimensions of the window.
    hide_address=False: bool
        Whether to show the address control for things like the Auber.
    """
    def __init__(self, api_class=None, name='serial_gui', show=True, block=False, window_size=[1,1], hide_address=False):

        # Remebmer the name.
        self.name = name

        # Checks periodically for the last exception
        self.timer_exceptions = _g.TimerExceptions()
        self.timer_exceptions.signal_new_exception.connect(self._new_exception)

        # Where the actual api will live after we connect.
        self.api = None
        self._api_class = api_class

        # GUI stuff
        self.window   = _g.Window(
            self.name, size=window_size, autosettings_path=name+'.window',
            event_close = self._window_close)
        
        # Top of GUI (Serial Communications)
        self.grid_top = self.window.place_object(_g.GridLayout(margins=False), alignment=0)
        self.window.new_autorow()

        # Get all the available ports
        self._label_port = self.grid_top.add(_g.Label('Port:'))
        self._ports = [] # Actual port names for connecting
        ports       = [] # Pretty port names for combo box
        if _comports:
            for p in _comports():
                self._ports.append(p.device)
                ports      .append(p.description)
        
        # Append simulation port
        ports      .append('Simulation')
        self._ports.append('Simulation')
        
        # Append refresh port
        ports      .append('Refresh - Update Ports List')
        self._ports.append('Refresh - Update Ports List')
        
        self.combo_ports = self.grid_top.add(_g.ComboBox(ports, autosettings_path=name+'.combo_ports'))
        self.combo_ports.signal_changed.connect(self._ports_changed)

        self.grid_top.add(_g.Label('Address:')).show(hide_address)
        self.number_address = self.grid_top.add(_g.NumberBox(
            1, 1, int=True,
            autosettings_path=name+'.number_address',
            tip='Address (not used for every instrument)')).set_width(40).show(hide_address)

        self.grid_top.add(_g.Label('Baud:'))
        self.combo_baudrates = self.grid_top.add(_g.ComboBox(
            ['1200', '2400', '4800', '9600', '19200'],
            default_index=3,
            autosettings_path=name+'.combo_baudrates'))

        self.grid_top.add(_g.Label('Timeout:'))
        self.number_timeout = self.grid_top.add(_g.NumberBox(50, dec=True, bounds=(1, None), suffix=' ms', tip='How long to wait for an answer before giving up (ms).', autosettings_path=name+'.number_timeout')).set_width(100)

        # Button to connect
        self.button_connect  = self.grid_top.add(_g.Button('Connect', checkable=True))

        # Stretch remaining space
        self.grid_top.set_column_stretch(self.grid_top._auto_column)

        # Connect signals
        self.button_connect.signal_toggled.connect(self._button_connect_toggled)
        
        # Status
        self.label_status = self.grid_top.add(_g.Label(''))

        # Expand the bottom grid
        self.window.set_row_stretch(1)
        
        # Error
        self.grid_top.new_autorow()
        self.label_message = self.grid_top.add(_g.Label(''), column_span=10).set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')

        # Other data
        self.t0 = None

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=name)

        # Show the window.
        if show: self.window.show(block)
    
    def _ports_changed(self):
        """
        Refreshes the list of availible serial ports in the GUI.
        """
        if self.get_selected_port() == 'Refresh - Update Ports List':
            
            len_ports = len(self.combo_ports.get_all_items())
            
            # Clear existing ports
            if(len_ports > 1): # Stop recursion!
                for n in range(len_ports):
                    self.combo_ports.remove_item(0)
            else:
                return
                self.combo_ports.remove_item(0)
                 
            self._ports = [] # Actual port names for connecting
            ports       = [] # Pretty port names for combo box
                
            default_port = 0
             
            # Get all the available ports
            if _comports:
                for inx, p in enumerate(_comports()):
                    self._ports.append(p.device)
                    ports      .append(p.description)
                    
                    if 'Arduino' in p.description:
                        default_port = inx
                        
            # Append simulation port
            ports      .append('Simulation')
            self._ports.append('Simulation')
            
            # Append refresh port
            ports      .append('Refresh - Update Ports List')
            self._ports.append('Refresh - Update Ports List')
             
            # Add the new list of ports
            for item in ports:
                self.combo_ports.add_item(item)
             
            # Set the new default port
            self.combo_ports.set_index(default_port)
    
    def _button_connect_toggled(self, *a):
        """
        Connect by creating the API.
        """
        if self._api_class is None:
            raise Exception('You need to specify an api_class when creating a serial GUI object.')

        # If we checked it, open the connection and start the timer.
        if self.button_connect.is_checked():
            port = self.get_selected_port()
            self.api = self._api_class(
                    port=port,
                    address=self.number_address.get_value(),
                    baudrate=int(self.combo_baudrates.get_text()),
                    timeout=self.number_timeout.get_value())
            
            # Delay to give the Arduino time to run setup
            _time.sleep(2)

            # Record the time if it's not already there.
            if self.t0 is None: self.t0 = _time.time()

            # Enable the grid
            self.grid_bot.enable()

            # Disable serial controls
            self.combo_baudrates.disable()
            self.combo_ports    .disable()
            self.number_timeout .disable()
            
            if self.api.simulation_mode:
                #self.label_status.set_text('*** Simulation Mode ***')
                #self.label_status.set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
                self.combo_ports.set_value(len(self._ports)-2)
                self.button_connect.set_text("Simulation").set_colors(background='pink')
            else:
                self.button_connect.set_text('Disconnect').set_colors(background = 'blue')

        # Otherwise, shut it down
        else:
            self.api.disconnect()
            #self.label_status.set_text('')
            self.button_connect.set_colors()
            self.grid_bot.disable()

            # Enable serial controls
            self.combo_baudrates.enable()
            self.combo_ports    .enable()
            self.number_timeout .enable()
            
            self.button_connect.set_text('Connect').set_colors(background = '')


        # User function
        self._after_button_connect_toggled()

    def _after_button_connect_toggled(self):
        """
        Dummy function called after connecting.
        """
        return

    def _new_exception(self, a):
        """
        Just updates the status with the exception.
        """
        self.label_message(str(a)).set_colors('red')

    def _window_close(self):
        """
        Disconnects. When you close the window.
        """
        print('Window closed but not destroyed. Use show() to bring it back.')
        if self.button_connect():
            print('  Disconnecting...')
            self.button_connect(False)

    def get_selected_port(self):
        """
        Returns the actual port string from the combo box.
        """
        return self._ports[self.combo_ports.get_index()]
    
    def get_com_ports():
        """
        Returns a dictionary of port names as keys and descriptive names as values.
        """
        if _comports:
    
            ports = dict()
            for p in _comports(): ports[p.device] = p.description
            return ports
    
        else:
            raise Exception('You need to install pyserial and have Windows to use get_com_ports().')
            
    def list_com_ports():
        """
        Prints a "nice" list of available COM ports.
        """
        ports = get_com_ports()
    
        # Empty dictionary is skipped.
        if ports:
            keys = list(ports.keys())
            keys.sort()
            print('Available Ports:')
            for key in keys:
                print(' ', key, ':', ports[key])
    
        else: raise Exception('No ports available. :(')

class temperature_controller(serial_gui_base):
    """
    Graphical interface for the Auber SYL-53X2P temperature controller.
    
    Parameters
    ----------
    name='auber_syl53x2p' : str
        Unique name to give this instance, so that its settings will not
        collide with other egg objects.
        
    temperature_limit=450 : float
        Upper limit on the temperature setpoint (C).
    
    show=True : bool
        Whether to show the window after creating.
        
    block=False : bool
        Whether to block the console when showing the window.
        
    window_size=[1,1] : list
        Dimensions of the window.
    """
    def __init__(self, name='test', temperature_limit=1000, show=True, block=False, window_size=[1,300]):

        # Remember the limit
        self._temperature_limit = temperature_limit

        # Run the base class stuff, which shows the window at the end.
        serial_gui_base.__init__(self, api_class=arduino_api, name=name, show=False, window_size=window_size)
        
        self.setup_gui_components(name, temperature_limit)
        
        # Finally show it.
        self.window.show(block)
    
    def _after_button_connect_toggled(self):
        
        if self.button_connect.is_checked():
            
            self._set_channel_status('Connected')
            
            self._send_parameters()

            self.timer.start()
        
        else:
            self._set_channel_status('Disconnected')
            self.timer.stop()       
            
    def _send_parameters(self):
        delim = ','
        msg = ''
        msg += str(int(self.number_setpoint_0      .get_value()*4))       + delim
        msg += str(int(round(self.number_band_0    .get_value()*4)))      + delim
        msg += str(int(round(self.number_integral_0.get_value()*1000*4))) + delim
        msg += str(int(round(self.number_rate_0    .get_value()*100)))   + delim
        
        msg += str(int(self.number_setpoint_1      .get_value()*4))       + delim
        msg += str(int(round(self.number_band_1    .get_value()*4)))      + delim
        msg += str(int(round(self.number_integral_1.get_value()*1000*4))) + delim
        msg += str(int(round(self.number_rate_1    .get_value()*100)))    + delim
        
        #print(msg)
        self.api.write(msg)
    
    def _set_channel_status(self, _status):
        if _status == 'Connected':
            self.channel_0_status.set_text('(Connected)').set_style('font-size: 20pt; color: mediumspringgreen')
            self.channel_1_status.set_text('(Connected)').set_style('font-size: 20pt; color: mediumspringgreen')
        else:
            self.channel_0_status.set_text('(Disconnected)').set_style('font-size: 20pt; color: coral')
            self.channel_0_status.set_text('(Disconnected)').set_style('font-size: 20pt; color: coral')

    def _timer_tick(self):
        t = _time.time()-self.t0
        
        packet = self.api.read_all()
        data = packet.split('\r\n')[:-1] 
        if(_debug): print(data)
        
        try:
            t0, output0, proportional0, integral0, t1, output1, proportional1, integral1, Tsample = data
            
            self.number_temperature_0.set_value(float(t0))
            self.number_temperature_1.set_value(float(t1))
        
            self.plot_0.append_row([t, float(t0), float(output0), float(proportional0), float(integral0)], ckeys=['Time (s)', 'Temperature (C)', 'Output (%)', 'Proportional', 'Integral'])
            self.plot_0.plot()
            
            self.plot_1.append_row([t, float(t1), float(output1), float(proportional1), float(integral1)], ckeys=['Time (s)', 'Temperature (C)', 'Output (%)', 'Proportional', 'Integral'])
            self.plot_1.plot()
        except:
            return
    
    def setup_gui_components(self, name, temperature_limit):
        # Remember the limit
        self._temperature_limit = temperature_limit

        # Run the base class stuff, which shows the window at the end.
        _serial_tools.serial_gui_base.__init__(self, api_class=arduino_api, name=name, show=False, window_size=[1000,800])
        
        self.window.set_size([0,0])
        
        self.grid_bot.new_autorow()
        
        # Add tabs to the bottom grid
        self.tabs = self.grid_bot.add(_g.TabArea(self.name+'.tabs'), alignment=0,column_span=10)
        
        # Create main tab
        self.tab_channel_0  = self.tabs.add_tab('Channel 0')
        self.tab_channel_1  = self.tabs.add_tab('Channel 1')
        
        # Channel 0 tab segmentation
        t01 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=0)
        t02 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=1)
        t03 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=2)
        t04 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=2, column = 0,column_span=10)
        
        t01.add(_g.Label('Temperature:'), alignment=2).set_style('font-size: 15pt; font-weight: bold; color: white')
        self.number_temperature_0 = t01.add(_g.NumberBox(
            -273.16, bounds=(-273.16, temperature_limit), suffix='°C',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; font-weight: bold; color: white' )
        t01.new_autorow()
        
        t01.add(_g.Label('Setpoint:'), alignment=2).set_style('font-size: 15pt; font-weight: bold; color: cyan' )
        self.number_setpoint_0 = t01.add(_g.NumberBox(
            25.4, bounds=(0, temperature_limit), suffix='°C',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: cyan').enable()
        
        t02.new_autorow()
        t02.add(_g.Label('Band:'), alignment=2).set_style('font-size: 15pt; color: paleturquoise')
        self.number_band_0 = t02.add(_g.NumberBox(
            5, bounds=(0, 1000), suffix='°C',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: paleturquoise').enable()

        t02.new_autorow()
        t02.add(_g.Label('Integral time:'), alignment=2).set_style('font-size: 15pt; color: gold')
        self.number_integral_0 = t02.add(_g.NumberBox(
            30, bounds=(0, 1000), suffix='s',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: gold').enable()
        
        t02.new_autorow()
        t02.add(_g.Label('Ramp rate:'), alignment=2).set_style('font-size: 15pt; color: pink')
        self.number_rate_0 = t02.add(_g.NumberBox(
            0.1, bounds=(0, 1000), suffix='s⁻¹',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: pink').enable()
        
        t03.add(_g.Label('Channel 0'), alignment=0, column=0, row=0).set_style('font-size: 20pt; color: royalblue')
        self.channel_0_status = t03.add(_g.Label('(Disconnected)'), alignment=0, column=0, row=1).set_style('font-size: 20pt; color: coral')

        # Make the Channel 0 plotter.
        self.plot_0 = t04.add(_g.DataboxPlot(
            file_type='*.csv',
            autosettings_path=name+'.plot',
            delimiter=',', show_logger=True), alignment=0, column_span=10)
        
        # Channel 0 tab segmentation
        t11 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=0)
        t12 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=1)
        t13 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=2)
        t14 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=3, column = 0,column_span=10)
        
        t11.add(_g.Label('Temperature:'), alignment=2).set_style('font-size: 15pt; font-weight: bold; color: white')
        self.number_temperature_1 = t11.add(_g.NumberBox(
            -273.16, bounds=(-273.16, temperature_limit), suffix='°C',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; font-weight: bold; color: white' )
        t11.new_autorow()
        
        t11.add(_g.Label('Setpoint:'), alignment=2).set_style('font-size: 15pt; font-weight: bold; color: cyan' )
        self.number_setpoint_1 = t11.add(_g.NumberBox(
            25.4, bounds=(0, temperature_limit), suffix='°C',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: cyan').enable()
        
        t12.new_autorow()
        t12.add(_g.Label('Band:'), alignment=2).set_style('font-size: 15pt; color: paleturquoise')
        self.number_band_1 = t12.add(_g.NumberBox(
            5, bounds=(0, 1000), suffix='°C',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: paleturquoise').enable()

        t12.new_autorow()
        t12.add(_g.Label('Integral time:'), alignment=2).set_style('font-size: 15pt; color: gold')
        self.number_integral_1 = t12.add(_g.NumberBox(
            30, bounds=(0, 1000), suffix='s',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: gold').enable()
        
        t12.new_autorow()
        t12.add(_g.Label('Ramp rate:'), alignment=2).set_style('font-size: 15pt; color: pink')
        self.number_rate_1 = t12.add(_g.NumberBox(
            0.1, bounds=(0, 1000), suffix='s⁻¹',
            signal_changed=self._send_parameters
            )).set_width(200).set_style('font-size: 15pt; color: pink').enable()
        
        t13.add(_g.Label('Channel 1'), alignment=0, column=0, row=0).set_style('font-size: 20pt; color: fuchsia')
        self.channel_1_status = t13.add(_g.Label('(Disconnected)')   , alignment=0, column=0, row=1).set_style('font-size: 20pt; color: coral')

        # Make the Channel 0 plotter.
        self.plot_1 = t14.add(_g.DataboxPlot(
            file_type='*.csv',
            autosettings_path=name+'.plot',
            delimiter=',', show_logger=True), alignment=0, column_span=10)

        # Timer for collecting data
        self.timer = _g.Timer(interval_ms=1000, single_shot=False)
        self.timer.signal_tick.connect(self._timer_tick)

        # Bottom log file controls
        self.grid_bot.new_autorow()

        return    


self = temperature_controller('Dominic`s Controller')