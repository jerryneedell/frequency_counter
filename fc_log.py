import serial
import time
import os
import sys
from pathlib import Path

port = ''

if len(sys.argv) != 2:
    print("Usage:python3 fc_log.py <PORT>")
    exit(0)

port = sys.argv[1]

ser = serial.Serial(port, 115200, timeout=1)
file_count = 0
file_open = False
idle_count = 0
try:
    while True:
        data = ser.read_until(expected=b'\n')
        if data == b'Started\r\n' :
            now = time.localtime()
            path = str(Path.home())+"/Desktop/"
            tag = "_".join([str(x) for x in now[0:6]])
            filename = path+"fc_log_"+tag+".csv"
            f = open(filename,"w")
            f.close()
            file_open = True
            data = None
            file_count += 1
        if file_open and data:
            line = data[0:-2].decode("UTF-8")
            line = line+"\n"
            print(line[0:-1])
            try:
                with open(filename,"a") as logfile:
                    logfile.write(line)
                    idle_count =  0
            except UnicodeDecodeError as e:
                print("decode error",e)
        else:
            idle_count += 1
            if data:
                print(".",end='',flush=True)
                if idle_count&0x3f == 0:
                    print("\nStop and Restart the Sensor")
            else:
                if idle_count&3 == 0:
                    print("Start the Sensor")


except KeyboardInterrupt:
    pass
except Exception as e:
    print("Some errror occured ",e)
