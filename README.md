# frequency_counter
frequency counter experimentation

* Reciprocal_frequency_counter_220219.py -- original code from https://forums.raspberrypi.com/viewtopic.php?t=306250
* freq.py -- uses original state machines -- writes .csv file to flash
* freq_gjn.py -- uses modified state machine per forum discussion -- not working  https://forums.raspberrypi.com/viewtopic.php?f=146&t=306250&p=1851876#p1841768

the test programs freq.py and freq_gjn.py use a button on GPIO 16 to trigger a sample -- GPIO 16 is pulled High and the button is is normally open and connected to Ground when pressed.
Pressing the button again halts the sample and waits for another button press to start again.
