#!/usr/bin/env python3

import json
import os
import sys
import jinja2

input_path = sys.argv[1]
output_path = sys.argv[2]

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates/")))
header_template = environment.get_template("header.jinja2")
source_template = environment.get_template("source.jinja2")

# Open each of the JSON files
for peripheral_path in os.listdir(input_path):
    if not peripheral_path.endswith(".json"):
        continue
    with open(os.path.join(input_path, peripheral_path), "r") as f:
        peripheral = json.load(f)

    os.makedirs(output_path, exist_ok=True)

    # Create the data format required by the templates
    peripheral_name = os.path.splitext(peripheral_path)[0]

    # TODO need the mask
    # TODO need to add the reserved values
    # TODO need the bit size of each register field
    # TODO need to deal with split bits
    # TODO need to know about arrays

    with open(os.path.join(output_path, f"{peripheral_name}.hpp"), "w") as header:
        header.write(header_template.render(peripheral_name=peripheral_name, peripheral=peripheral))

    with open(os.path.join(output_path, f"{peripheral_name}.cpp"), "w") as source:
        source.write(source_template.render(peripheral_name=peripheral_name, peripheral=peripheral))
