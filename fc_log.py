import serial
import time
import os
import sys

port = ''

if len(sys.argv) != 2:
    print("Usage:python3 fc_log.py <PORT>")
    exit(0)

port = sys.argv[1]

ser = serial.Serial(port, 115200)
file_count = 0
file_open = False
while True:
    #data = ser.read(ser.inWaiting())
    data = ser.read_until(expected=b'\n')
    #print(data)
    if data == b'Started\r\n' :
        now = time.localtime()
        tag = "_".join([str(x) for x in now[0:6]])
        filename = "fc_log_"+tag+".csv"
        f = open(filename,"w")
        f.close()
        file_open = True
        data = None
        file_count += 1
    if file_open and data:
        #if data[len(data)-1] != 0 :
        #    print("null terminator missing\rn")
        #print([hex(x) for x in data])
        print(data)
        try:
            with open(filename,"a") as logfile:
                logfile.write(data.decode("UTF-8"))
        except UnicodeDecodeError as e:
            print("decode error",e)
    else:
        print(".",end='',flush=True)
