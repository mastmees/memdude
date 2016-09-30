# The MIT License (MIT)
#
# Copyright (c) 2015 Madis Kaal <mast@nomad.ee>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# You need PyUSB (https://github.com/walac/pyusb/blob/master/docs/tutorial.rst)
#
import usb.core
import usb.util
import time
import sys
import binascii

#
# For schematics, see https://learn.adafruit.com/assets/6834
# It would be wise to replace R7 and R4 with a lower value somewhere
# around 500 ohms, as 1.5K may cause the clock signal distortion
# to the point wher false clock pulses will be detected
#
#
# AVR PORTB bit numbers            25LCxxx wiring
# in USBtinyISP                      +--------+
# 0 - LED                      VCC  -+ 1    8 +- VCC
# 1                            MISO -+ 2    7 +- VCC
# 2                            VCC  -+ 3    6 +- SCK
# 3                            GND  -+ 4    5 +- MOSI
# 4 - RESET                          +--------+
# 5 - MOSI
# 6 - MISO
# 7 - SCK

class usbtiny:

  def __init__(self):
    self.USBTINY_ECHO = 0          #echo test
    self.USBTINY_READ = 1          #read port B pins
    self.USBTINY_WRITE = 2         #write byte to port B
    self.USBTINY_CLR = 3           #clear PORTB bit, value=bit number (0..7)
    self.USBTINY_SET = 4           #set PORTB bit, value=bit number (0..7)
    self.USBTINY_POWERUP = 5       #apply power and enable buffers, value=sck-period, index=RESET
    self.USBTINY_POWERDOWN = 6     #remove power from chip, disable buffers
    self.USBTINY_SPI = 7           #spi command, value=c1c0, index=c3c2
    self.USBTINY_POLL_BYTES = 8    #set poll bytes for write, value=p1p2
    self.USBTINY_FLASH_READ = 9    #read flash, index=address, USB_IN reads data
    self.USBTINY_FLASH_WRITE = 10  #write flash, index=address,value=timeout, USB_OUT writes data
    self.USBTINY_EEPROM_READ = 11  #read eeprom, index=address, USB_IN reads data
    self.USBTINY_EEPROM_WRITE = 12 #write eeprom, index=address,value=timeout, USB_OUT writes data
    self.USBTINY_DDRWRITE = 13     #set port direction, value=DDRB register value
    self.USBTINY_SPI1 = 14         #single byte SPI command, value=command
    # these values came from avrdude (http://www.nongnu.org/avrdude/)
    self.USBTINY_RESET_LOW = 0     #for POWERUP command
    self.USBTINY_RESET_HIGH = 1    #for POWERUP command
    self.USBTINY_SCK_MIN = 1       #min sck-period for POWERUP
    self.USBTINY_SCK_MAX = 250     #max sck-period for POWERUP
    self.USBTINY_SCK_DEFAULT = 10  #default sck-period to use for POWERUP
    self.USBTINY_CHUNK_SIZE = 128
    self.USBTINY_USB_TIMEOUT = 500 #timeout value for writes
    # search for usbtiny
    self.dev=usb.core.find(idVendor=0x1781,idProduct=0x0c9f)
    if self.dev==None:
      print "USBtiny programmer not connected"
      exit(1)
    self.dev.set_configuration()
    return

  def _usb_control(self,req,val,index,retlen=0):
    return self.dev.ctrl_transfer(usb.util.CTRL_IN|usb.util.CTRL_RECIPIENT_DEVICE|usb.util.CTRL_TYPE_VENDOR,req,val,index,retlen)
    
  def power_on(self):
    self._usb_control(self.USBTINY_POWERUP, self.USBTINY_SCK_DEFAULT, self.USBTINY_RESET_HIGH )

  def power_off(self):
    self._usb_control(self.USBTINY_POWERDOWN,0,0)

  def write(self,portbbits):
    self._usb_control(self.USBTINY_WRITE,portbbits,0)
    
  def read(self):
    return self._usb_control(self.USBTINY_READ,0,0,1)
  
  def spi1(self,b):
    return self._usb_control(self.USBTINY_SPI1,b,0,1)
  
  def spi4(self,d1d0,d3d2):
    return self._usb_control(self.USBTINY_SPI,d1d0,d3d2,4)
    
  def clr(self,bit):
    self._usb_control(self.USBTINY_CLR,bit,0)

  def set(self,bit):
    self._usb_control(self.USBTINY_SET,bit,0)

# 25LCxxxx eeprom basic functions

class eeprom:

  def __init__(self):
    self.dev=usbtiny()
    self.CS_BIT=4
    self.SI_BIT=5
    self.SO_BIT=6
    self.CLK_BIT=7
    self.adrsize=2
  
  def set_adrsize(self,adrsize_bytes):
    self.adrsize=adrsize_bytes
    
  def power_on(self):
    self.dev.power_on()
  
  def power_off(self):
    self.dev.power_off()
    
  def cs_low(self):
    self.dev.clr(self.CS_BIT)

  def cs_high(self):
    self.dev.set(self.CS_BIT)
    
  def spi1(self,c):
    d=self.dev.spi1(c)
    return d[0]

  def read_status_register(self):
    self.cs_low()
    self.spi1(0x5)
    d=self.spi1(0)
    self.cs_high()
    return d

  def enable_write(self):
    self.cs_low()
    self.spi1(0x06)
    self.cs_high()

  def chip_erase(self):
    self.enable_write()
    self.cs_low()
    self.spi1(0xc7)
    self.cs_high()
    self.ready_wait()

  def set_write_address(self,adr):
    self.cs_low()
    self.spi1(0x02)
    if self.adrsize>2:
      self.spi1((adr>>16)&0xff)
    self.spi1((adr>>8)&0xff)
    self.spi1(adr&0xff)

  def write_byte(self,b):
    self.spi1(b)

  def set_read_address(self,adr):
    self.cs_low()
    self.spi1(0x03)
    if self.adrsize>2:
      self.spi1((adr>>16)&0xff)
    self.spi1((adr>>8)&0xff)
    self.spi1(adr&0xff)
  
  def read_byte(self):
    return self.spi1(0)

  def ready_wait(self):
    while 1:
      if (self.read_status_register()&1)==0:
        break

  def write_block(self,adr,data):
    self.enable_write()
    self.set_write_address(adr)
    for c in data:
      self.write_byte(c)
    self.cs_high()
    self.ready_wait()
  
  def read_block(self,adr,count):
    self.set_read_address(adr)
    d=[]
    while count:
      d.append(self.read_byte())
      count=count-1
    self.cs_high()
    return d

class FormatException(Exception):
  def __init__(self, value):
     self.value = value
  def __str__(self):
     return str(self.value)

def program_hex(filename,memsize,pagesize,adrsize,verify):
  device=eeprom()
  device.set_adrsize(adrsize)
  device.power_on()
  baseadr=0
  for l in open(filename):
    if l[0]!=":":
      raise FormatException("%s does not begin with ':'"%l)
    b=binascii.unhexlify(l[1:].strip())
    bytecount=ord(b[0])
    adr=(ord(b[1])<<8)|ord(b[2])
    type=ord(b[3])
    data=[]
    for c in b[4:bytecount+4]:
      data.append(ord(c))
    chksum=ord(b[bytecount+4])
    sum=0
    for c in b[0:bytecount+4]:
      sum=sum+ord(c)
    sum=(~sum)&0xff
    sum=(sum+1)&0xff
    if sum!=chksum:
      raise FormatException("Invalid checksum %02x!=%02x"%(chksum,sum))
    if type==0: #data
      beginadr=baseadr+adr
      if beginadr+len(data)>memsize:
        # this should usually work out fine but if records
        # are not aligned on page boundary then the entire record will not
        # be written even though some data may actually fit in
        raise FormatException("Data exceeds memory size") 
      print "\r%08x"%(beginadr+len(data)),
      sys.stdout.flush()
      if beginadr%pagesize!=0: # not at page boundary
        space=pagesize-(beginadr%pagesize)
        if len(data)<space:
          space=len(data)
        device.write_block(beginadr,data[:space])
        beginadr=beginadr+space
        data=data[space:]
      #now at page boundary, write in up to page size chunks
      while len(data)>0:
        if bytecount<=pagesize:
          device.write_block(beginadr,data)
          break
        else:
          device.write_block(beginadr,data[:pagesize])
          beginadr=beginadr+pagesize
          data=data[pagesize:]
      if verify:
        # read back and compare
        beginadr=baseadr+adr
        data=[]
        for c in b[4:bytecount+4]:
          data.append(ord(c))
        rdata=device.read_block(beginadr,bytecount)
        if data!=rdata:
          raise FormatExeption("Verification failed")        
    elif type==1:
      break
    elif type==2:
      if bytecount!=2:
        raise FormatException("Extended segment address not 2 bytes")
      a=(ord(data[0])<<8)|ord(data[1])
      baseadr=a*16
    elif type==3:
      continue    #CS:IP register content, just ignore it
    elif type==4:
      if bytecount!=2:
        raise FormatException("Extended linear address not 2 bytes")
      a=(ord(data[0])<<8)|ord(data[1])
      baseadr=a<<16
    elif type==5:
      continue    #EIP register content, also ignored
  print ""
  device.power_off()

def program_binary(filename,memsize,pagesize,adrsize,verify):
  device=eeprom()
  device.set_adrsize(adrsize)
  device.power_on()
  adr=0
  f=open(filename,"rb")
  while 1:
    s=f.read(pagesize)
    if len(s)==0:
      break
    if adr+len(s)>memsize: # as we are writing in page size chunks,
                           # we end up writing as much as the chip fits
      raise FormatException("Data exceeds memory size")
    data=[]
    for c in s:
      data.append(ord(c))
    device.write_block(adr,data)
    if verify:
      rdata=device.read_block(adr,len(data))
      if data!=rdata:
        raise FormatException("Verification failed")        
    adr=adr+len(s)
    print "%08x\r"%(adr),
    sys.stdout.flush()
  f.close()
  device.power_off()
  print ""
  return


def printhelp():
  print "use: python memdude --write --device devicename [--verify] [--hex|--bin] filename"
  print "     python memdude --read [--device devicename] [--adr adr --count bytecount] filename"
  print "     python memdude --erase --device devicename"
  print "supported devices:\n    ",
  for d in devices:
    print d,
  print ""
  exit(0)

format=''
filename=None
devicename=None
operation=''
address=0
readcount=0
verify=False

# unfortunately only 2 largest devices support chip erase
#
devices= {
  "25lc1024": {"id":0x29,"size":128*1024,"pagesize":256,"chiperase":1, "adrsize":3},
  "25lc512":  {"id":0x29,"size":64*1024, "pagesize":256,"chiperase":1, "adrsize":2},
  "25lc256":  {"id":0xff,"size":32*1024, "pagesize":64, "chiperase":0, "adrsize":2},
  "25lc128":  {"id":0xff,"size":16*1024, "pagesize":64, "chiperase":0, "adrsize":2},
  "25lc640":  {"id":0xff,"size":8*1024,  "pagesize":32, "chiperase":0, "adrsize":2},
  "25lc320":  {"id":0xff,"size":4*1024,  "pagesize":32, "chiperase":0, "adrsize":2},
  "25lc160":  {"id":0xff,"size":2*1024,  "pagesize":16, "chiperase":0, "adrsize":2},
  "25lc080":  {"id":0xff,"size":1024,    "pagesize":16, "chiperase":0, "adrsize":2},
  "25lc040":  {"id":0xff,"size":512,     "pagesize":16, "chiperase":0, "adrsize":2},
  "25lc020":  {"id":0xff,"size":256,     "pagesize":16, "chiperase":0, "adrsize":2},
  "25lc010":  {"id":0xff,"size":128,     "pagesize":16, "chiperase":0, "adrsize":2}
}

args=sys.argv[1:]

while len(args):
  arg=args.pop(0)
  if arg=='--hex':
    format='hex'
  elif arg=='--bin':
    format='bin'
  elif arg=='--verify':
    verify=True
  elif arg=='--read':
    operation='read'
  elif arg=='--write':
    operation='write'
  elif arg=='--erase':
    operation='erase'
  elif arg=='--adr':
    address=int(args.pop(0))
    continue
  elif arg=='--count':
    readcount=int(args.pop(0))
    continue
  elif arg=='--device':
    devicename=args.pop(0).lower()
    if devicename not in devices:
      print "unsupported device %s"%devicename
      exit(1)
  elif arg in ('-h','--h','--help'):
    printhelp()
  else:
    filename=arg

if devicename==None:
  printhelp()

if operation=='erase':
  print "erasing device"
  device=eeprom()
  device.set_adrsize(devices[devicename]["adrsize"])
  device.power_on()
  try:
    if devices[devicename]["chiperase"]>0:
      device.chip_erase()
    else:
      print "chip erase command not supported, writing 0xff-s"
      bytecount=devices[devicename]["size"]
      pagesize=devices[devicename]["pagesize"]
      adr=0
      block=[]
      for i in range(0,pagesize):
        block.append(0xff)
      while adr<bytecount:
        sys.stdout.flush()
        device.write_block(adr,block)
        adr+=pagesize
        print "%08x\r"%(adr),
        sys.stdout.flush()
  except KeyboardInterrupt:
    device.power_off()
    exit(1)
  device.power_off()
  print ""
  exit(0)

if filename==None:
  printhelp()

if operation=='write':
  if format=='':
    if '.hex' in filename:
      format='hex'
    else:
      format='.bin'
  print "programming device"
  try:
    if format=='hex':
      program_hex(filename,devices[devicename]["size"],devices[devicename]["pagesize"], \
        devices[devicename]["adrsize"],verify)
    else:
      program_binary(filename,devices[devicename]["size"],devices[devicename]["pagesize"], \
        devices[devicename]["adrsize"],verify)
  except FormatException as e:
    print ""
    print e
    device=eeprom()
    device.power_off()
    exit(1)
  except IOError as e:
    print e
    device=eeprom()
    device.power_off()
    exit(1)
  except KeyboardInterrupt:
    device=eeprom()
    device=eeprom()
    device.power_off()
    exit(1)
  exit(0)
  
if operation=='read':
  if readcount==0:
    readcount=devices[devicename]["size"]
  print "reading %d bytes from %08x into %s"%(readcount,address,filename)
  device=eeprom()
  device.power_on()
  device.set_adrsize(devices[devicename]["adrsize"])
  try:
    f=open(filename,"wb")
    while readcount:
      if readcount>devices[devicename]["pagesize"]:
        c=devices[devicename]["pagesize"]
      else:
        c=readcount
      d=device.read_block(address,c)
      s=""
      for ch in d:
        s=s+chr(ch)
      f.write(s)
      readcount=readcount-c
      address=address+c
      print "\r%08x"%address,
      sys.stdout.flush()
    f.close()
  except IOError as e:
    print e
  except KeyboardInterrupt:
    device.power_off()
    exit(1)
  print ""
  device.power_off()
  exit(0)
  
printhelp()
