import spinmob.egg   as _egg
import spinmob       as _s
import time          as _time
import serial        as _serial

_g            = _egg.gui

from serial.tools.list_ports import comports as _comports
from _serial_gui_base  import serial_gui_base
from _arduino_api      import arduino_api

# GUI settings
_s.settings['dark_theme_qt'] = True

# Print data to terminal for debugging
_debug = True


class temperature_controller(serial_gui_base):
    """
    Graphical interface for the Dominic Ryan's Arduino based
    temperature controller.
    
    Parameters
    ----------
    name='test' : str
        Unique name to give this instance, so that its settings will not
        collide with other egg objects.
        
    temperature_limit=1000 : float
        Upper limit on the temperature setpoint (C).
    
    show=True : bool
        Whether to show the window after creating.
        
    block=False : bool
        Whether to block the console when showing the window.
        
    window_size=[1,300] : list
        Dimensions of the window.
    """
    def __init__(self, name='test', temperature_limit=1000, show=True, block=False, window_size=[1,300]):

        # Remember the limit
        self._temperature_limit = temperature_limit

        # Run the base class stuff, which shows the window at the end.
        serial_gui_base.__init__(self, api_class=arduino_api, name=name, show=False, window_size=window_size)
        
        # Populate the GUI with all the goods
        self.setup_gui_components(name, temperature_limit)
        
        # Finally show it.
        self.window.show(block)
    
    def _after_button_connect_toggled(self):
        
        if self.button_connect.is_checked():
            
            # Indicate channel status in the GUI            
            self._set_channel_status('Connected')
            
            # Send the PID parameters to the arduino
            self._send_parameters()

            # Start the GUI timer
            self.timer.start()
        
        else:
            # Indicate channel status in the GUI  
            self._set_channel_status('Disconnected')
            
            # Stop GUI timer
            self.timer.stop()       
            
    def _send_parameters(self):
        """
        Sends the temperature control parameters to the arduino controller.

        """
        delim = ','
        
        # Build up the message to send to the controller
        msg = ''
        msg += str(int(self.number_setpoint_0      .get_value()*4))       + delim
        msg += str(int(round(self.number_band_0    .get_value()*4)))      + delim
        msg += str(int(round(self.number_integral_0.get_value()*1000*4))) + delim
        msg += str(int(round(self.number_rate_0    .get_value()*100)))    + delim
        
        msg += str(int(self.number_setpoint_1      .get_value()*4))       + delim
        msg += str(int(round(self.number_band_1    .get_value()*4)))      + delim
        msg += str(int(round(self.number_integral_1.get_value()*1000*4))) + delim
        msg += str(int(round(self.number_rate_1    .get_value()*100)))    
        
        # Write the message to the arduino
        if(_debug): print('msg: %s' %msg)
        self.api.write(msg)
        
        # Write a single char to start the arduino's loop
        self.api.write('a')
    
    def _set_channel_status(self, _status):
        """
        Updates the channel status (Connected or Disconnected) in the GUI.
        
        """
        
        if _status == 'Connected':
            self.channel_0_status.set_text('(Connected)').set_style('font-size: 20pt; color: mediumspringgreen')
            self.channel_1_status.set_text('(Connected)').set_style('font-size: 20pt; color: mediumspringgreen')
        else:
            self.channel_0_status.set_text('(Disconnected)').set_style('font-size: 20pt; color: coral')
            self.channel_0_status.set_text('(Disconnected)').set_style('font-size: 20pt; color: coral')
            
    
    def _timer_tick(self):
        """
        Called every time the timer ticks. Used for grabbing serial data and updating the GUI.
        """
        
        # Get the time
        t = _time.time()-self.t0
        
        # Grab data packet fromt he serial line
        packet = self.api.read_all()
        
        # Split by the Serial.println() delimiter
        data = packet.split('\r\n')[:-1] 
        
        # Print to console for debugging
        if(_debug): 
            print("Recovered Data: ")
            print(data)
        
        try:
            # Try to seperate the data
            T0, output0, proportional0, integral0, T1, output1, proportional1, integral1, Tsample = data
            
            # Update temperature number boxes
            self.number_temperature_0     .set_value(float(T0))
            self.number_temperature_1     .set_value(float(T1))
            self.number_temperature_sample.set_value(float(Tsample))
        
            # Update data plots
            self.plot_0.append_row([t, float(T0), float(output0), float(proportional0), float(integral0)], ckeys=['Time (s)', 'Temperature (C)', 'Output (%)', 'Proportional', 'Integral'])
            self.plot_0.plot()
            
            self.plot_1.append_row([t, float(T1), float(output1), float(proportional1), float(integral1)], ckeys=['Time (s)', 'Temperature (C)', 'Output (%)', 'Proportional', 'Integral'])
            self.plot_1.plot()
            
            self.plot_sample.append_row([t, float(Tsample)], ckeys=['Time (s)', 'Temperature (C)'])
            self.plot_sample.plot()
            
            # Print data packet status to console
            if(_debug): print("Packet accepted!")
        except:
            
            # Print data packet status to console
            if(_debug): print("Packet NOT accepted.")
            return
    
    def setup_gui_components(self, name, temperature_limit):
        """
        Sets up the GUI layout (Numberboxes, Plotters, ect..)
        """
        
        # Remember the limit
        self._temperature_limit = temperature_limit
        
        self.window.set_size([0,0])
        
        self.grid_bot.new_autorow()
        
        # Add tabs to the bottom grid
        self.tabs = self.grid_bot.add(_g.TabArea(self.name+'.tabs'), alignment=0,column_span=10)
        
        # Create main tab
        self.tab_channel_0       = self.tabs.add_tab('Channel 0')
        self.tab_channel_1       = self.tabs.add_tab('Channel 1')
        self.tab_channel_sample  = self.tabs.add_tab('Sample')
        
        # Channel 0 tab segmentation
        t01 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=0)
        t02 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=1)
        t03 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=2)
        t04 = self.tab_channel_0.place_object(_g.GridLayout(margins=False), alignment=0, row=2, column = 0,column_span=10)
        
        # Add relevant numberboxes for realtime channel 0 data
        t01.add(_g.Label('Temperature:'), alignment=2).set_style('font-size: 15pt; font-weight: bold; color: white')
        self.number_temperature_0 = t01.add(_g.NumberBox(
            -273.16, bounds=(-273.16, temperature_limit), suffix='°C')).set_width(200).set_style('font-size: 15pt; font-weight: bold; color: white' ).disable()
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
        
        # Channel 1 tab segmentation
        t11 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=0)
        t12 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=1)
        t13 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=1,column=2)
        t14 = self.tab_channel_1.place_object(_g.GridLayout(margins=False), alignment=0, row=2, column = 0,column_span=10)
        
        # Add relevant numberboxes for realtime channel 1 data
        t11.add(_g.Label('Temperature:'), alignment=2).set_style('font-size: 15pt; font-weight: bold; color: white')
        self.number_temperature_1 = t11.add(_g.NumberBox(
            -273.16, bounds=(-273.16, temperature_limit), suffix='°C')).set_width(200).set_style('font-size: 15pt; font-weight: bold; color: white' ).disable()
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

        # Make the Channel 1 plotter.
        self.plot_1 = t14.add(_g.DataboxPlot(
            file_type='*.csv',
            autosettings_path=name+'.plot',
            delimiter=',', show_logger=True), alignment=0, column_span=10)
        
        # Sample channel tab segmentation
        tS1 = self.tab_channel_sample.place_object(_g.GridLayout(margins=False), alignment=0, row=0, column =0)
        tS2 = self.tab_channel_sample.place_object(_g.GridLayout(margins=False), alignment=0, row=1, column = 0,column_span=10)
        
        # Add relevant numberboxe for realtime sample channel data
        tS1.add(_g.Label('Sample Temperature:'), alignment=1).set_style('font-size: 15pt; font-weight: bold; color: white')
        self.number_temperature_sample = tS1.add(_g.NumberBox(
            -273.16, bounds=(-273.16, temperature_limit), suffix='°C')).set_width(200).set_style('font-size: 15pt; font-weight: bold; color: white' ).disable()
        
        # Make the Sample Channel plotter.
        self.plot_sample = tS2.add(_g.DataboxPlot(
            file_type='*.csv',
            autosettings_path=name+'.plot',
            delimiter=',', show_logger=True), alignment=0, column_span=10)

        # Timer for collecting data
        self.timer = _g.Timer(interval_ms=500, single_shot=False)
        self.timer.signal_tick.connect(self._timer_tick)

        # Bottom log file controls
        self.grid_bot.new_autorow()

        return    

# Create an instance of the controller
if __name__ == '__main__':
    self = temperature_controller('Dominic`s Controller')