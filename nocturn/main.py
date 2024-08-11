from usb_client import dev, SingleCommands, ParsedCommand
from midi_client import startup
from rtmidi.midiconstants import CONTROL_CHANGE  # midi reference list

# todo:
#  config1:
#    v encoders
#    v send midi
#    shift button
#    swap 2 encoders
#    move to end
#  state:
#    copy
#    midi map for each state
#  delayed commands like wait until X time passed
#  encoder speed customize
#  interact with osc
#  ref to use socketserver or thread instead of loop


def func(arg: ParsedCommand):
    # for every enc value
    #  writes to led
    # button
    #  toggles state
    command, k, v = arg
    if command.standard_command:
        if command.encoder:
            dev.batch_write(SingleCommands.Encoder, ks=k, vs=v)
        if command.button:
            dev.set_state(k)
    return arg


def func(arg: ParsedCommand):
    # for every enc value
    #  update led
    #  midi-out stored value
    command, k, v = arg
    if command.standard_command:
        if command.encoder:
            dev.batch_write(SingleCommands.Encoder, ks=k, vs=v)
            midiout.send_message([CONTROL_CHANGE, k, dev[command, k]])
    return arg


midiin, midiout = startup()

dev.looping_func = func
dev.loop_blocking()
