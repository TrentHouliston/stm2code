import re


def normalise_input(peripheral_name, register_name, txt):

    # USB OTG breaks the pattern and adds for read and for pop to the offset fields
    if peripheral_name == "OTG":
        txt = txt.replace("Address offset for read:", "Address offset:")
        txt = txt.replace("Address offset for pop:", "Address offset:")

    # OPAMP just uses address: not address offset;
    if peripheral_name in ("OPAMP", "OPAMP1", "OPAMP2"):
        txt = txt.replace("Address:", "Address offset:")

    # Replace Backup domain reset value with Reset value for RTC
    if peripheral_name == "RTC":
        txt = txt.replace("Backup domain reset value:", "Reset value:")

    return txt


# Correct weird lines that should have been written differently to fit the pattern
def normalise_offset(peripheral_name, register_name, txt):

    # RAMECC decided to "simplify" one of them which just made it different
    if peripheral_name == "RAMECC":
        if register_name == "MxCR" and txt == "0x20*x":
            txt = "0x20+0x20*(x-1),(x=ECCmonitoringunitnumber)"

        # TODO it's 1-5 for d1 and d2, but 1-2 for d3 and they're monitoring different things so it's kinda not really relevant
        txt = txt.replace("x=ECCmonitoringunitnumber", "x=1to5")

    # HRTIM has this on many of the offset values which are for different register groups
    if peripheral_name == "HRTIM":
        txt = txt.replace("(thisoffsetaddressisrelativetotimerxbaseaddress)", "")

        # HRTIM_BDTxUPR there's just one of these for each of A B C D E
        if txt == "0x3DCh-0x3ECh":
            txt = "0x3DC+0x04*x,(x=0to4)"

    # RTC backup registers, there's just a bunch of these
    if peripheral_name == "RTC" and register_name == "BKPxR" and txt == "0x50to0xCC":
        txt = "0x50+0x4*x,(x=0to31)"

    return txt


def extract_range(r):
    if groups := re.match(r"([xy])=(\d+)to(\d+)", r):
        return (groups.group(1), int(groups.group(2), base=0), int(groups.group(3), base=0))
    elif groups := re.match(r"([xy])=(\d+)", r):
        return (groups.group(1), int(groups.group(2), base=0), int(groups.group(2), base=0))
    else:
        raise ValueError(f"Invalid range: {r}")


def address_offset(peripheral_name, register_name, txt):

    # Normalise abnormal descriptions for the offset in the pdf
    txt = normalise_input(peripheral_name, register_name, txt)

    # Address Offset: (...) Reset Value:
    address_offset = re.search(r"Address offset:(.+?)(?:Reset|$)", txt, re.MULTILINE | re.IGNORECASE)

    # Can't find an offset
    if not address_offset:
        return None

    # Remove the rest of the text except for the offset and remove any whitespace from it
    txt = re.sub(r"\s+", "", address_offset.group(1).strip())

    # Normalise abnormal offsets from the pdf
    txt = normalise_offset(peripheral_name, register_name, txt)

    # Offset is a simple hex value
    if groups := re.match(r"^(0x[0-9A-F]+)h?$", txt, re.IGNORECASE):
        return int(groups.group(1), 16)

    # A or B style
    elif groups := re.match("^(0x[0-9A-F]+)or(0x[0-9A-F]+)$", txt, re.IGNORECASE):
        # return (groups.group(1), groups.group(2))
        # todo wut do these A or B things are a little weird it implies that both work
        return int(groups.group(1), 16)

    # Range styles that should match as groups (base, offset, range)
    range_patterns_1d = [
        # 0x000 + 0x4 * x, (x = 0 to 31)
        # 0x000 + 0x4 * (x-1), (x = 0 to 31)
        r"^(?P<base>0x[0-9A-F]+)\+(?P<size>0x[0-9A-F]+)\*(?P<symbol>[xy]|\([xy]-1\)),?\((?P<range>[xy]=\d+(?:to\d+)?)\)$",
        # 0x050 + x * 0x4 (x = 0 to 7)
        # 0x050 + (x-1) * 0x4 (x = 0 to 7)
        r"^(?P<base>0x[0-9A-F]+)\+(?P<symbol>[xy]|\([xy]-1\))\*(?P<size>0x[0-9A-F]+),?\((?P<range>[xy]=\d+(?:to\d+)?)\)$",
        # 0x000 + 0x04 * x, where x = 0 to 7
        r"^(?P<base>0x[0-9A-F]+)\+(?P<size>0x[0-9A-F]+)\*(?P<symbol>[xy]),where(?P<range>[xy]=\d+(?:to\d+)?)$",
    ]
    if groups := next(
        (v for v in (re.match(p, txt, re.IGNORECASE) for p in range_patterns_1d) if v is not None),
        None,
    ):
        # TODO if it's x-1 or y-1 then subtract 1 from each end of the range
        base = int(groups.group("base"), base=0)
        size = int(groups.group("size"), base=0)
        symbol = groups.group("symbol")
        limits = extract_range(groups.group("range"))
        if limits[0] not in symbol:
            raise ValueError(f"Symbol {symbol} does not match the range {limits[0]}")

        return (base, (size, symbol, limits))

    # Range styles that have two dimensions (x and y)
    range_patterns_2d = [
        # 0x050+0x40*x+0x4*y,(x=0to3;y=0to15)
        r"^(?P<base>0x[0-9A-F]+)\+(?P<size1>0x[0-9A-F]+)\*(?P<symbol1>[xy])\+(?P<size2>0x[0-9A-F]+)\*(?P<symbol2>[xy]),\((?P<range1>[xy]=\d+(?:to\d+)?);(?P<range2>[xy]=\d+(?:to\d+)?)\)$",
    ]
    if groups := next(
        (v for v in (re.match(p, txt, re.IGNORECASE) for p in range_patterns_2d) if v is not None),
        None,
    ):
        base = int(groups.group("base"), base=16)

        size1 = int(groups.group("size1"), base=16)
        symbol1 = groups.group("symbol1")
        limits1 = extract_range(groups.group("range1"))

        size2 = int(groups.group("size2"), base=16)
        symbol2 = groups.group("symbol2")
        limits2 = extract_range(groups.group("range2"))

        if limits1[0] not in symbol1:
            raise ValueError(f"Symbol {symbol1} does not match the range {limits1[0]}")
        if limits2[0] not in symbol2:
            raise ValueError(f"Symbol {symbol2} does not match the range {limits2[0]}")

        return (base, (size1, symbol1, limits1), (size2, symbol2, limits2))

    return None
