from usb_client import dev, SingleCommands, ParsedCommand,listen_and_output_midi
from midi_client import startup
from rtmidi.midiconstants import * # midi reference list

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
    # wip: device with 9 encoders * 16 states via buttons.
    # for every enc value
    #  writes to led
    # button
    #  toggles state
    command, k, v = arg
    if command.standard_command:
        if command.encoder:
            dev.batch_write(SingleCommands.Encoder, ks=k, vs=v)
        if command.button and k!=16: # dial btn
            dev.set_state(k)
    return arg


midiin, midiout = startup()

dev.looping_func = listen_and_output_midi
dev.loop_blocking()



