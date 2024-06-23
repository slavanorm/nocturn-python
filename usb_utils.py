# for usb debugging, unused here
def usb_info(self, dev):

    def print_basic(dev):
        try:
            if dev._manufacturer is None:
                dev._manufacturer = usb.util.get_string(
                    dev, dev.iManufacturer
                )
        except Exception as e:
            print("Exception: {}".format(e))
        try:
            if dev._product is None:
                dev._product = usb.util.get_string(
                    dev, dev.iProduct
                )
        except Exception as e:
            print("Exception: {}".format(e))
        stx = "USB VID: 0x{:04X} PID: 0x{:04X} Mfr name '{}' Product '{}'".format(
            dev.idVendor,
            dev.idProduct,
            str(dev._manufacturer).strip(),
            str(dev._product).strip(),
        )
        print(stx)

    def print_internals(dev):  # SO: 18224189
        for attrib in dir(dev):
            if (
                not attrib.startswith("_")
                and not attrib == "configurations"
            ):
                try:
                    x = getattr(dev, attrib)
                    print("  ", attrib, x)
                except Exception as e:
                    print(
                        "Exception for attrib '{}': {}".format(
                            attrib, e
                        )
                    )
        try:
            for config in dev.configurations():
                for attrib in dir(config):
                    if not attrib.startswith("_"):
                        try:
                            x = getattr(config, attrib)
                            print("  ", attrib, x)
                        except Exception as e:
                            print(
                                "Exception for attrib '{}': {}".format(
                                    attrib, e
                                )
                            )
        except Exception as e:
            print(
                "Exception config in dev.configurations: {}".format(
                    e
                )
            )

    def print_cfg(dev):
        for cfg in dev:
            print(str(cfg.bConfigurationValue))
            for intf in cfg:
                print(
                    "\t"
                    + str(intf.bInterfaceNumber)
                    + ","
                    + str(intf.bAlternateSetting)
                    + "\n"
                )
            for ep in intf:
                print("\t\t" + str(ep.bEndpointAddress))
    def get_endpoints(dev, cfg_index):
        cfg_list = dev.get_active_configuration()

        cfg_value = cfg_list[cfg_index]

        ep_out = usb.util.find_descriptor(
            cfg_value,
            # match the first OUT endpoint
            custom_match=lambda e: usb.util.endpoint_direction(
                e.bEndpointAddress
            )
            == usb.util.ENDPOINT_OUT,
        )

        # 0x2

        ep_in = usb.util.find_descriptor(
            cfg_value,
            custom_match=lambda e: usb.util.endpoint_direction(
                e.bEndpointAddress
            )
            == usb.util.ENDPOINT_IN,
        )

        assert ep_in is not None
        # 0x81
        return {"in": ep_in, "out": ep_out}
    """
    endpoints = get_endpoints(dev, (0, 0))
    # 3 == 11 in binary
    ep_in_type = usb.util.endpoint_type(
        endpoints["in"].bmAttributes
    )
    ep_out_type = usb.util.endpoint_type(
        endpoints["out"].bmAttributes
    )
    
    """

    # for dev in usb.core.find(find_all=True):  # SO:9577601
    print(type(dev))  # <class 'usb.core.Device'>
    print_basic(dev)
    print_internals(dev)
    print_cfg(dev)
