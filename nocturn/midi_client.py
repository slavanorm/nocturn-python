from abc import abstractmethod
import time
import rtmidi
from rtmidi.midiconstants import (
    # midi reference list
    CONTROL_CHANGE,
    NOTE_ON,
    NOTE_OFF,
)
#from usb_client import FinalDevice,dev

CC_NUMBERS_TO_LISTEN = [0, 1]  # range(1,127)


class MidiInHandler:
    def __call__(self, event, *args):
        # called on every midi event. this prepares data for self.call
        event, delta = event
        info, key, value = event
        status = info & 0xF0
        channel = info & 0xF

        if self.filter_events(status, channel):
            self.handle_event(status, channel, key, value)

    @abstractmethod
    def handle_event(self, status, channel, key, value):
        pass

    def filter_events(self, status, channel):
        # could be overriden
        return (
            status == CONTROL_CHANGE
            and channel == self.ch
            # and key in self.ccs
        )


class StoringHandler(MidiInHandler):
    """Records last value of Control Change events.

    The main loop prints out last seen value of specific Control Change events
    every second. The control change events are received by a MIDI input
    callback, which gets called on every MIDI event received and runs
    independently from the main loop.
    """

    def __init__(self, usb_device, channel=1, controllers=None, **kwargs):
        self.ch = channel - 1  # first ch is 0
        self.ccs = controllers or ()
        self.usb_device:FinalDevice = usb_device  # cc:value storage
        # todo: integrate this session with usb device class
        # add multiple channel support if necessary
        super().__init__()

    def handle_event(self, status, channel, key, value):
        self.usb_device[key] = value
        print(f"{key=},{value=}")

    def get(self, cc, default=63):
        # default getter could be customized here
        r= self.usb_device[cc]
        if r is None:
            r = default
        return r


def startup(real_ports=False):
    # midiin recieves, midiout produces midi signals
    # this is going to use virtual ports, if system allows creation. 
    # if error happens, one could try with real_ports True, but ports should be selected properly.
    midiin = rtmidi.MidiIn()
    midiout = rtmidi.MidiOut()
    if real_ports:
        midiin.open_port(1)
        midiout.open_port(0)
    else:
        midiin.open_virtual_port("From-nocturn")
        midiout.open_virtual_port("To-nocturn")
    return midiin, midiout


def cleanup_on_interrupt(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:
            pass
        finally:
            for e in args:
                del e
            for v in kwargs.values():
                del v

    return wrapper


def send_note_example(midiout: rtmidi.MidiOut):
    # this could be used to test midiinput
    note_on = [
        NOTE_ON,
        60,
        112,
    ]  # channel 1, middle C, velocity 112
    note_off = [NOTE_OFF, 60, 0]
    midiout.send_message(note_on)
#    time.sleep(0.5)
#    midiout.send_message(note_off)
#    time.sleep(0.1)


def send_cc_example(midiout: rtmidi.MidiOut,k_cc:int,v_cc:int):
    # this could be used to test midiinput
    msg = [
        CONTROL_CHANGE,
        k_cc,
        v_cc,
    ]
    midiout.send_message(msg)


def store_example_1(midiin: rtmidi.MidiIn):
    handler = StoringHandler(usb_device=dev, controllers=CC_NUMBERS_TO_LISTEN)
    midiin.set_callback(handler)

    with midiin:
        while True:
            for cc in CC_NUMBERS_TO_LISTEN:
                print("CC #%i: %s" % (cc, handler.get(cc)))

            print("--- ")
            time.sleep(3)

def store_example_2(midiin: rtmidi.MidiIn):
    handler = StoringHandler(usb_device=dev, controllers=CC_NUMBERS_TO_LISTEN)
    midiin.set_callback(handler)
    while True:
        pass

if __name__ == "__main__":
    midiin, midiout = startup()
    # midiin recieves, midiout produces midi signals
    
    #store_example_2(midiin)
    #with midiout:
    send_cc_example(midiout,1,2)
    v=1
    #store_example_2(midiin)
