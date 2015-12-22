#memdude
Use USBtinyISP to read and write Microchip 25LCxx EEPROM devices

The software is written in Python and demonstrates use of PyUSB
using USBtiny as USB connected I/O device.

For schematics of USBtinyISP, see https://learn.adafruit.com/assets/6834

It would be wise to replace R7 and R4 with a lower value somewhere
around 500 ohms, as 1.5K may cause the clock signal distortion
to the point wher false clock pulses will be detected, depending
on your setup.

<pre>
 AVR PORTB bit numbers            25LCxxx wiring
 in USBtinyISP                      
                                    +--------+
 0 - LED                      VCC  -+ 1    8 +- VCC
 1                            MISO -+ 2    7 +- VCC
 2                            VCC  -+ 3    6 +- SCK
 3                            GND  -+ 4    5 +- MOSI
 4 - RESET                          +--------+
 5 - MOSI
 6 - MISO
 7 - SCK
</pre>
