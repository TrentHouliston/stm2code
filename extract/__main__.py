#!/usr/bin/env python3

# Find documentation for the fields in the PDF
import pypdf
import re
import json
import os
from collections import defaultdict
import sys

from fields import fields

input_path = sys.argv[1]
output_path = sys.argv[2]

pdf = pypdf.PdfReader(sys.argv[1])

from register_sections import register_sections
from simplify_reserved import simplify_reserved
from address_offset import address_offset
from group import group

# Final peripherals output
peripherals = defaultdict(lambda: defaultdict(list))

# Process each of the register sections of the PDF file
for peripheral_name, register_name, register_description, txt in register_sections(pdf):

    group_name = peripheral_name

    if peripheral_name == "GPIO" and register_name.startswith("x_"):
        register_name = register_name[2:]

    # If peripheral name is ADC and register name starts with `x_` then it's actually the ADC common register
    if peripheral_name == "ADC" and register_name.startswith("x_"):
        group_name = "COMMON"
        register_name = register_name[2:]

    # Get the address offset for the register
    offset = address_offset(peripheral_name, register_name, txt)
    if offset is None:
        raise ValueError(f"Address offset not found for {peripheral_name}_{register_name}")

    # Add the peripheral to the list
    peripherals[peripheral_name][group_name].append(
        {
            "name": register_name,
            "description": register_description,
            "offset": offset,
            "fields": fields(peripheral_name, register_name, txt),
        }
    )

# Combine any reserved fields into a single reserved field with the combined bitset
simplify_reserved(peripherals)

# Work out the array/substruct fields from their offsets
group(peripherals)

# Format the number fields using hexidecimal format
for peripheral_name, groups in peripherals.items():
    for group_name, registers in groups.items():
        for register in registers:
            if isinstance(register["offset"], int):
                register["offset"] = "0x{:02X}".format(register["offset"])

# Validate the output data
#  - Check for overlapping registers in the same peripheral # same offsets or the array size makes it overlap
#  - Check for overlapping fields in the same register # bits collide


# convert the map into a list of registers
peripherals_path = os.path.join(output_path, "peripherals")
os.makedirs(peripherals_path, exist_ok=True)
for peripheral, registers in peripherals.items():
    # Pull the name into the register
    json.dump(
        registers,
        open(os.path.join(peripherals_path, f"{peripheral}.json"), "w"),
        indent=4,
    )
