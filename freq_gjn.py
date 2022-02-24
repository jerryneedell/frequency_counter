    
    
    #Reciprocal frequency counter - Raspberry Pi Forum - horuable
#https://forums.raspberrypi.com/viewtopic.php?t=306250
# modified by Jerry Needell February 22, 2022 for use by Brian King
from micropython import const
import rp2
from rp2 import PIO, asm_pio
import machine
import time
  
@asm_pio(sideset_init=PIO.OUT_HIGH)
def gate():
    """PIO to generate gate signal."""
    wait(0, pin, 0)
    wrap_target()
    mov(x, osr)
    wait(1, pin, 0) # Probably not needed, since at this point signal will be high anyway
    label("loopstart")
    jmp(x_dec, "loopstart") .side(0)
    wait(0, pin, 0)
    wait(1, pin, 0) .side(1)
    irq(noblock, 0)
    wrap()

@asm_pio()
def clock_count():
    """PIO for counting clock pulses during gate low."""
    wait(1, pin, 0)
    wrap_target()
    mov(x, osr)
    wait(0, pin, 0)
    label("counter")
    jmp(pin, "output")
    jmp(x_dec, "counter")
    label("output")
    mov(isr, x)
    push()

@asm_pio(sideset_init=PIO.OUT_HIGH)
def pulse_count():
    """PIO for counting incoming pulses during gate low."""
    wait(1, pin, 0)
    wrap_target()
    mov(x, osr)
    wait(0, pin, 0) .side(0)
    label("counter")
    wait(0, pin, 1)
    wait(1, pin, 1)
    jmp(pin, "output")
    jmp(x_dec, "counter")
    label("output")
    mov(isr, x) .side(1)
    push()
    wrap()


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
    print("Press Button to start/stop")
    while button.value():
        pass
        
    update_flag = False
    data = array.array("I", [0, 0])
    def counter_handler(sm):
        print("IRQ")
        global update_flag
        if not update_flag:
            sm0.put(125_000)
            sm0.exec("pull()")
            data[0] = sm1.get() # clock count
            data[1] = sm2.get() # pulse count
            update_flag = True
    
    sm0, sm1, sm2 = init_sm(125_000_000, Pin(15, Pin.IN, Pin.PULL_UP), Pin(14, Pin.OUT), Pin(13, Pin.OUT))
    sm0.irq(counter_handler)
                
    print("Started")
    i = 0
    #f = open('freq_data.csv','w')
    #f.write("sample, time, clock, pulses, frequency\r\n")
    #f.close()

    while True:
        #print(update_flag)
        if update_flag:
            clock_count = 2*(max_count - data[0]+1)
            pulse_count = max_count - data[1]
            freq = pulse_count * (125000208.6 / clock_count)
            time_tag = time.ticks_ms()
            sample = (i,time_tag,clock_count,pulse_count,freq)
            print(sample)
            #time.sleep(.0001)
            #print("{}, {}, {}, {}, {}".format(i, time.ticks_ms(),clock_count,pulse_count,freq))
            #print(', '.join([str(x) for x in sample]))
            #with open('freq_data.csv','a') as f:
            #    f.write("{}, {}, {}, {}, {}\r\n".format(i,time.ticks_ms(),clock_count,pulse_count,freq))
            i += 1
            update_flag = False
            
            if time.ticks_ms() - button_time > 1000 and not button.value():
                run = False
                button_time = time.ticks_ms()
                print("stopped")
                machine.soft_reset()
        

    