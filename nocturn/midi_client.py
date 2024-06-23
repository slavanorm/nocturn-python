import time
import rtmidi
from rtmidi.midiconstants import (
    # midi reference list
    CONTROL_CHANGE,
    NOTE_ON,
    NOTE_OFF,
)



class MidiInHandler:
    """Records last value of Control Change events.

    The main loop prints out last seen value of specific Control Change events
    every second. The control change events are received by a MIDI input
    callback, which gets called on every MIDI event received and runs
    independently from the main loop.

    """

    def __init__(self, channel=1, controllers=None):
        self.ch = channel - 1  # first ch is 0
        self.ccs = controllers or ()
        self.session = dict()
        self.session[1] = 31

    def __call__(self, event, *args):
        event, delta = event
        status = event[0] & 0xF0
        ch = event[0] & 0xF

        if (
            status == CONTROL_CHANGE
            and ch == self.ch
            and event[1] in self.ccs
        ):
            self.session[event[1]] = event[2]

    def get(self, cc, default=63):
        return self.session.get(cc, default)


def startup():
    midiout_base = rtmidi.MidiOut()
    midiin_base = rtmidi.MidiIn()

    midiout = midiout_base.open_virtual_port("From-nocturn")
    midiin = midiin_base.open_virtual_port("To-nocturn")
    return midiin, midiout


def midi_cleanup(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:
            pass
        finally:
            for e in args:
                del e
            for k, v in kwargs.items():
                del v

    return wrapper


@midi_cleanup
def send(midiout):
    with midiout:
        note_on = [
            NOTE_ON,
            60,
            112,
        ]  # channel 1, middle C, velocity 112
        note_off = [NOTE_OFF, 60, 0]
        midiout.send_message(note_on)
        time.sleep(0.5)
        midiout.send_message(note_off)
        time.sleep(0.1)


# todo: write to session
@midi_cleanup
def store(midiin):
    CONTROLLERS = [0, 1]  # range(1,127)

    handler = MidiInHandler(controllers=CONTROLLERS)
    midiin.set_callback(handler)

    with midiin:
        while True:
            for cc in CONTROLLERS:
                print("CC #%i: %s" % (cc, handler.get(cc)))

            print("--- ")
            time.sleep(1)


if __name__ == "__main__":
    midiin, midiout = startup()

    store(midiin)
