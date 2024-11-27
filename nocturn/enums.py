from typing import Union

# command types and commands. syntax sugar


class MyField:
    def __init__(self, name=None, value=None, parent=None):
        self.name = name
        self.value = value
        self.parent = parent
        super().__init__()

    @property
    def encoder(self):
        return "encoder" in self.value

    @property
    def button(self):
        return "button" in self.value

    @property
    def touch(self):
        return "touch" in self.value

    @property
    def style(self):
        return "style" in self.value

    @property
    def fader(self):
        return "fader" in self.value

    @property
    def standard_command(self):
        return not self.send and (self.style or self.button or self.encoder or self.fader)

    @property
    def send(self):
        return "send" in self.value

    def __repr__(self) -> str:
        return " ".join(f"{e}" for e in self.value if e is not None)

    def __iter__(self):
        return iter(self.value)


class MyEnumMeta(type):
    def __new__(cls, name, bases, attrs: list[MyField]):
        # Access and potentially merge class attribute dictionaries
        merged_attrs = {}
        for base in bases:
            merged_attrs.update(getattr(base, "__dict__", {}))
            merged_attrs.update(attrs)

        merged_attrs["__all__"] = [
            attr for attr, value in merged_attrs.items() if not callable(value)
        ]

        cls = super().__new__(cls, name, bases, merged_attrs)

        for k, v in merged_attrs.items():
            # print(self, k, v)
            if "__" not in k:
                if isinstance(v, MyField):
                    v = MyField(k, v.value, cls)
                else:
                    v = MyField(k, v, cls)
                setattr(cls, k, v)

        return cls

    def __contains__(self, other):
        if isinstance(other, MyField):
            return hasattr(self, other.name)
        else:
            return other in self.items()

    def __instancecheck__(self, other):
        if isinstance(other, MyField):
            return other.parent in self.__mro__

    def __iter__(self):
        return iter(e for e in self.__all__ if not "__" in e)

    def items(self):
        return self.__dict__.items()


class MyEnum(MyField, metaclass=MyEnumMeta):
    # this is used over enum.Enum as Enum doesnt allow composition

    # allows Union-style annotation
    def __or__(self, other):
        return Union[self.__class__, other]

    def __ror__(self, other):
        return Union[self.__class__, other]


def args_or_list_of_args(func):
    def inner(cls, *args, **kwargs):
        if isinstance(args[0], list) and len(args) == 1:
            return [
                func(cls, e, **kwargs)
                if not isinstance(e,(tuple,list))
                else func(cls,*e,**kwargs)
                for e in args[0]
            ]
        return func(cls, *args, **kwargs)

    return inner


class ReadWriteCommands(MyEnum):
    Encoder = "encoder", ""
    Button = "button", ""


class ReadCommands(MyEnum):
    Fader = "fader", None
    Touch = "touch", None


class WriteCommands(MyEnum):
    Button_invert = "button", "_invert"
    Button_on = "button", "_on"
    Button_off = "button", "_off"

    Encoder_on = "encoder", "_on"
    Encoder_off = "encoder", "_off"
    Style = "style", ""


class SingleCommands(ReadCommands, WriteCommands, ReadWriteCommands):
    # used in usb_*() functions
    pass


class BatchCommands(SingleCommands):
    # enum with global commands, usable in batch_write()
    Off = "send", 0, 0
    Brightness_half = "send", 0, 126
    Brightness_full = "send", 0, 127


RawReadCommand = list[int, int, int]
RawWriteCommand = list[int, int]
ParsedCommand = list[SingleCommands, int, int]
