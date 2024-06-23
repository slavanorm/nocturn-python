from usb_client import dev, SingleCommands, BatchCommands, ParsedCommand

# todo:
#  config1:
#   encoders
#    swap 2
#    move to end
#  state:
#   copy
#  delayed commands like wait until X time passed, output curves
#  encoder speed customize
#  interact with midi osc and ableton


def func(arg: ParsedCommand):
    command, k, v = arg
    if command.standard_command:
        if command.encoder:
            dev.batch_write(SingleCommands.Encoder, ks=k, vs=v)
        if command.button:
            dev.set_state(k)
            v = 1
    return arg


dev.looping_func = func
dev.loop_blocking()
