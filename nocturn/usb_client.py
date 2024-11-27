from typing import Callable
from unittest import result
import usb.core
import usb.util
from enums import *
import time
import itertools
from rtmidi.midiconstants import NOTE_ON, CONTROL_CHANGE  # midi reference list


def myrange(len, start=None):
    return [e for e in range(start, start + len)]


# device management


class SerialDevice:
    # class only with usb interaction, code not supposed to be changed
    config = dict(
        device=dict(idVendor=0x1235, idProduct=0x000A),
        endpoints=dict(ep_out=0x2, ep_in=0x81, packetsize=8),
        timeout=10,
        init_command=(0, 0, 176),
    )

    def __init__(self):
        dev: usb.core.Device = usb.core.find(**self.config["device"])
        if not dev:
            raise ValueError("no nocturn found")
        dev.set_configuration()
        self.dev = dev
        # self.usb_info(self.dev)
        self.usb_write(*self.config["init_command"])
        super().__init__()

    def usb_read(self) -> RawReadCommand:
        r = []
        try:
            r = self.dev.read(
                self.config["endpoints"]["ep_in"],
                self.config["endpoints"]["packetsize"],
                self.config["timeout"],
            )
        except usb.core.USBTimeoutError:
            pass

        return list(r)[:3]

    @args_or_list_of_args
    def usb_write(
        self, *command: RawWriteCommand | BatchCommands
    ) -> RawWriteCommand:
        # returns only for debugging purpose
        # actual writing command
        if len(command) == 1:
            command = command[0]
        if command in BatchCommands:
            if command.send:
                command = command.value[1:]
            else:
                raise NotImplemented
        if None in command:
            return
        try:
            r = self.dev.write(
                self.config["endpoints"]["ep_out"],
                command,
                self.config["timeout"],
            )
        except usb.USBError:
            return
        assert r == len(command), "Check if all bytes were sent"
        return command


class RunnableMixin:
    looping_func: Callable[[ParsedCommand], ParsedCommand] = None

    # configurations specific to read/write and loop employing them
    def loop_blocking(
        self, func: Callable[[ParsedCommand], ParsedCommand] = None, write=True
    ):
        if func is None and self.looping_func is not None:
            func = self.looping_func
        while True:
            r = self.usb_read()
            r1 = self.usb_parse(r)
            r2 = self.usb_filter(r1)
            if not r2:
                continue
            # if func is not None:
            r3 = func(r2)
            if r3:
                print(*r3)
            # elif write:
            #    self.usb_write(*r2)
            #    print(*r2)
            time.sleep(0.001 * self.config["timeout"])

    def usb_parse(self, command: RawReadCommand) -> ParsedCommand:
        # listens to input, preparing it for storing in self.state
        if not command:
            return
        value = command[2]
        cc = command[1]

        def encoder_mapping(value):
            if value < 64:
                # {0:-1,1:-2,2:-3,3:-4,4:-5}
                value = value + 1
            else:
                # {127:1,126:2,125:3,124:4,123:5}
                value = value - 128
            return value

        if cc > 63 and cc < 72:
            return (
                SingleCommands.Encoder,
                cc - 64,
                encoder_mapping(value),
            )
        if cc == 74:
            # enc dial is 8
            return (
                SingleCommands.Encoder,
                8,
                encoder_mapping(value),
            )
        if cc == 72:
            # crossfader
            if value in (0, 127):
                # ignore crossfader spam/not intelligible
                return
            return SingleCommands.Fader, 0, value

        if cc > 111 and cc < 128:
            return (
                SingleCommands.Button,
                cc - 112,
                value,
            )
        if cc == 81:
            # btn dial
            return (
                SingleCommands.Button,
                16,
                value,
            )

        if cc == 82:
            # t dial
            return SingleCommands.Touch, 9, value
        if cc == 83:
            # t crossfader
            return SingleCommands.Touch, 10, value
        if cc > 94 and cc < 104:
            return SingleCommands.Touch, cc - 95, value

    def usb_filter(self, usb_command: ParsedCommand) -> ParsedCommand:
        if usb_command is None:
            return
        command, cc, value = usb_command
        if command.fader:
            if value in (0, 127):
                # ignore crossfader spam/not intelligible
                return
        if command.touch:
            return
            if cc in (0, 1, 7, 8, 10):
                # 2 side-most touches spam/not intelligible
                return
        if command == SingleCommands.Button and value == 0:
            # ignore writing state of dial button
            return
        return usb_command


class StatefulMixin:
    def __init__(self):
        self.state_number = 0
        self.state_class:State = State
        self.states = [self.state_class(self, e) for e in range(16)]
        super().__init__()
        self.startup()

    def add_state(self):
        self.states += [State()]

    def set_state(self, state_number=0):
        print("using state:", state_number)
        if not state_number:
            state_number = 0
        self.state_number = state_number
        self.states[self.state_number].load()

    def __get_set_handler(self, k):
        result = self.states[self.state_number]
        if not isinstance(k, (tuple, list)):
            k = [k]
        if len(k)==1:
            k = ['encoder', "value", k]
        elif len(k) == 2:
            k = [k[0], "value", k[1]]
        for e in k[:-1]:
            if isinstance(e, MyField):
                if e.standard_command:
                    e = e.value[0]
                else:
                    e = e.value
            result = result[e]
        return result, k[-1]

    def __getitem__(self, k):
        result, k = self.__get_set_handler(k)
        return result[k]

    def __setitem__(self, k, v):
        result, k = self.__get_set_handler(k)
        if result[k] == v:
            raise ValueError
        result[k] = v

    def get(self,k,default):
        try:
            r=result[k]
        except KeyError:
            r = default
        return r

    def get_key(self,k):
        result,k= self.__get_set_handler(k)
        return k
    
    def startup(self, commands: list[BatchCommands] = None):
        self.batch_write([BatchCommands.Brightness_full, *commands])
        self.set_state()


class State(dict):
    def __init__(self, owner: StatefulMixin, name):
        self.owner = owner
        self["encoder"] = dict(
            # enc 8 is dial
            value=9
            * [64],  # 0..11 *12 <127
        )
        self["style"] = dict(
            # enc 8 is dial
            value=9
            * [0],  #  0..8 *16
        )
        self["button"] = dict(
            # btn 0 is dial
            value=17 * [0],  # 0|1
            # style 126 | 127 ?
        )
        # touch enc + dial + fader
        self["touch"] = dict(value=10 * [0])
        self["fader"] = dict(value=[0])

        self["button"][name] = 127

    def load(self):
        self.owner.batch_write(BatchCommands.Button, store_in_state=False)

        self.owner.batch_write(BatchCommands.Style, store_in_state=False)
        self.owner.batch_write(BatchCommands.Encoder, store_in_state=False)


class WriteableMixin:

    @args_or_list_of_args
    def batch_write(
        self,
        command: BatchCommands,
        vs: int | list = None,
        ks: int | list = None,
        store_in_state=True,
    ):  # -> single_write[ParsedCommand] | usb_write[RawWriteCommand]
        # force avoids storing at self.state. used for state.load()
        if command.send:
            return self.usb_write(command.value[1:])
        if command.encoder or command.style:
            length = 9
        elif command.button:
            length = 16

        if isinstance(ks, int):
            ks = [ks]
        if not isinstance(vs, list):
            vs = itertools.repeat(vs)
        if not ks:
            ks = range(length)

        myiter = zip(ks, vs)
        for k, v in myiter:
            self.single_write(command, k, v, store_in_state)

    def single_write(
        self,
        command: SingleCommands,
        k: int,
        v: int = None,
        store_in_state=True,
    ):  # -> SerialDevice.usb_write[RawWriteCommand]
        v = self.manage_value(command, k, v)
        run = True
        if store_in_state:
            run = self.store_value(command, k, v)
        if run:
            k = self.manage_usb_address(command, k)
            if k:
                return self.usb_write(k, v)

    def store_value(self, command: SingleCommands, k, v):
        try:
            self[command, k] = v
            return True
        except ValueError:
            # v is already present at command,k
            pass

    def manage_usb_address(self, command: SingleCommands, k: int):
        usb_address = False
        if command.style:
            usb_address = myrange(8, 72) + [81]
        elif command.encoder:
            usb_address = myrange(8, 64) + [80]
        elif command.button:
            usb_address = myrange(16, 112) + [None]
        if usb_address:
            return usb_address[k]

    def manage_value(self, command: SingleCommands, k, v=None):
        if v is None:
            v = self[command, k]
        else:
            if command.encoder:
                v += self[command, k]

            if command == SingleCommands.Button_invert:
                v = 127 * (not self[command, k])

            if "_on" in command:
                v = 127
            if "_off" in command:
                v = 0

            v = max(v, 0)
            v = min(v, 127)
        return v


class FinalDevice(SerialDevice, RunnableMixin, StatefulMixin, WriteableMixin):
    def startup(self):
        super().startup(
            [
                (BatchCommands.Style, 16 * 3),
            ]
        )


class Config1State(State):
    def load(self):
        # doesnt *load* buttons
        self.owner.batch_write(BatchCommands.Style, store_in_state=False)
        self.owner.batch_write(BatchCommands.Encoder, store_in_state=False)


class Config1(FinalDevice):
    #   buttons to toggle 16 banks for 9 encoders
    state_class = Config1State


dev = Config1()

# sample options for dev.loop_blocking()
listen_inputs = lambda x: x
listen_and_write_usb = lambda x: dev.single_write(x)


def listen_and_batch_write(arg: ParsedCommand):
    command, k, v = arg
    if command.standard_command:
        if command.encoder:
            dev.batch_write(BatchCommands.Encoder, v)  #
        if command.button:
            dev.batch_write(BatchCommands.Button_invert)
    return arg


def listen_and_output_midi(arg: ParsedCommand):
    # for every enc value
    #  update led
    #  midi-out stored value
    command, k, v = arg
    if command.standard_command:
        
        if command.encoder:
            v=v*2
            dev.batch_write(SingleCommands.Encoder, ks=k, vs=v)
            midiout.send_message([CONTROL_CHANGE, k, dev[command, k]])
        if command.fader:
            dev.batch_write(SingleCommands.Fader, ks=k, vs=v)
            midiout.send_message([CONTROL_CHANGE, 127, dev[command, k]])
        if command.button and k!=16:
            # sends 127 and 0
            dev.batch_write(SingleCommands.Button_invert, ks=k, vs=v)
            midiout.send_message([NOTE_ON, k, v])
    return arg
