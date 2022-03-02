#Reciprocal frequency counter - Raspberry Pi Forum - horuable
#https://forums.raspberrypi.com/viewtopic.php?t=306250
# modified by Jerry Needell February 22, 2022 for use by Brian King
from micropython import const
import rp2
from rp2 import PIO, asm_pio
import machine
import time
import os
  
@asm_pio(sideset_init=PIO.OUT_HIGH)
def gate():
    """PIO to generate gate signal."""
    mov(x, osr)                                            # load gate time (in clock pulses) from osr
    wait(0, pin, 0)                                        # wait for input to go low
    wait(1, pin, 0)                                        # wait for input to go high - effectively giving us rising edge detection
    label("loopstart")
    jmp(x_dec, "loopstart") .side(0)                       # keep gate low for time programmed by setting x reg
    wait(0, pin, 0)                                        # wait for input to go low
    wait(1, pin, 0) .side(1)                               # set gate to high on rising edge
    irq(block, 0)                                          # set interrupt 0 flag and wait for system handler to service interrupt
    wait(1, irq, 4)                                        # wait for irq from clock counting state machine
    wait(1, irq, 5)                                        # wait for irq from pulse counting state machine

@asm_pio()
def clock_count():
    """PIO for counting clock pulses during gate low."""
    mov(x, osr)                                            # load x scratch with max value (2^32-1)
    wait(1, pin, 0)                                        # detect falling edge
    wait(0, pin, 0)                                        # of gate signal
    label("counter")
    jmp(pin, "output")                                     # as long as gate is low //
    jmp(x_dec, "counter")                                  # decrement x reg (counting every other clock cycle - have to multiply output value by 2)
    label("output")
    mov(isr, x)                                            # move clock count value to isr
    push()                                                 # send data to FIFO
    irq(block, 4)                                          # set irq and wait for gate PIO to acknowledge

@asm_pio(sideset_init=PIO.OUT_HIGH)
def pulse_count():
    """PIO for counting incoming pulses during gate low."""
    mov(x, osr)                                            # load x scratch with max value (2^32-1)
    wait(1, pin, 0)                                        
    wait(0, pin, 0) .side(0)                               # detect falling edge of gate
    label("counter")
    wait(0, pin, 1)                                        # wait for rising
    wait(1, pin, 1)                                        # edge of input signal
    jmp(pin, "output")                                     # as long as gate is low //
    jmp(x_dec, "counter")                                  # decrement x req counting incoming pulses (probably will count one pulse less than it should - to be checked later)
    label("output") 
    mov(isr, x) .side(1)                                   # move pulse count value to isr and set pin to high to tell clock counting sm to stop counting
    push()                                                 # send data to FIFO
    irq(block, 5)                                          # set irq and wait for gate PIO to acknowledge


def init_sm(freq, input_pin, gate_pin, pulse_fin_pin):
    """Starts state machines."""
    gate_pin.value(1)
    pulse_fin_pin.value(1)
    max_count = const((1 << 32) - 1)
    
    sm0 = rp2.StateMachine(0, gate, freq=freq, in_base=input_pin, sideset_base=gate_pin)
    sm0.put(freq)
    sm0.exec("pull()")
    
    sm1 = rp2.StateMachine(1, clock_count, freq=freq, in_base=gate_pin, jmp_pin=pulse_fin_pin)
    sm1.put(max_count)
    sm1.exec("pull()")
    
    sm2 = rp2.StateMachine(2, pulse_count, freq=freq, in_base=gate_pin, sideset_base = pulse_fin_pin, jmp_pin=gate_pin)
    sm2.put(max_count-1)
    sm2.exec("pull()")
    
    sm1.active(1)
    sm2.active(1)
    sm0.active(1)
    
    return sm0, sm1, sm2

    
if __name__ == "__main__":
    from machine import Pin
    import uarray as array
    button = machine.Pin(16,machine.Pin.IN,machine.Pin.PULL_UP)
    button_time = 0
    time.sleep(1)
    print("Press Button to start/stop")
    fs_info=os.statvfs("/")
    fs_full= int(100*(fs_info[3]/fs_info[2]))
    print("file system free percent: ",fs_full)
    while button.value():
        pass
        
    update_flag = False
    data = array.array("I", [0, 0])
    def counter_handler(sm):
        #print("IRQ")
        global update_flag
        if not update_flag:
            sm1.active(0)
            sm2.active(0)
            #print("flagged")
            sm0.put(125000)
            sm0.exec("pull()")
            data[0] = sm1.get() # clock count
            data[1] = sm2.get() # pulse count
            update_flag = True    
    sm0, sm1, sm2 = init_sm(125_000_000, Pin(15, Pin.IN, Pin.PULL_UP), Pin(14, Pin.OUT), Pin(13, Pin.OUT))
    sm0.irq(counter_handler)
                
    print("Started")
    i = 0
    now='_'.join([str(x) for x in time.localtime()[0:6]])
    filename="freq_data_"+now+".csv"
    f = open(filename,'w')
    f.write("sample, time, clock, pulses, frequency\r\n")
    f.close()
    keep_running=True
    while keep_running:
        #print(update_flag)
        if update_flag:
            clock_count = 2*(max_count - data[0]+1)
            pulse_count = max_count - data[1]
            freq = pulse_count * (125000208.6 / clock_count)
            time_tag = time.ticks_ms()
            #sample = (i,time_tag,clock_count,pulse_count,freq)
            #print(sample)
            #time.sleep(.0001)
            print("{}, {}, {}, {}, {}".format(i, time_tag,clock_count,pulse_count,freq))
            #print(', '.join([str(x) for x in sample]))
            with open(filename,'a') as f:
                f.write("{}, {}, {}, {}, {}\r\n".format(i,time_tag,clock_count,pulse_count,freq))
            i += 1
            if i&0xff == 0: # print file system status every 256 samples
                fs_info=os.statvfs("/")
                fs_full= int(100*(fs_info[3]/fs_info[2]))
                print("file system free percent: ",fs_full)
                if fs_full < 10 :
                    print("file system almost full - delete some files")
                    keep_running=False
                    sm1.active(0)
                    sm2.active(0)
                    sm0.active(0)
            update_flag = False
            sm1.active(1)
            sm2.active(1)
            if time.ticks_ms() - button_time > 1000 and not button.value():
                run = False
                button_time = time.ticks_ms()
                print("stopped")
                sm1.active(0)
                sm2.active(0)
                sm0.active(0)
                time.sleep(1)
                print("Press Button to start/stop")
                fs_info=os.statvfs("/")
                fs_full= int(100*(fs_info[3]/fs_info[2]))
                print("file system free percent: ",fs_full)
                while button.value():
                    pass
                now='_'.join([str(x) for x in time.localtime()[0:6]])
                filename="freq_data_"+now+".csv"
                f = open(filename,'w')
                f.write("sample, time, clock, pulses, frequency\r\n")
                f.close()
                sm1.active(1)
                sm2.active(1)
                sm0.active(1)
                i = 0
                button_time = time.ticks_ms()
                

        