import re
from itertools import groupby


def get_group_name(regs):

    # Get the first word of the description for each register
    vs = [r["description"].split(" ")[0] for r in regs]

    # Check they are all the same word
    if len(set(vs)) != 1:
        raise ValueError(f"Group name mismatch {vs}")

    # Return the first word of the description as the group name
    return vs[0].upper()


def group(peripherals):

    updates = []
    for peripheral_name, groups in peripherals.items():
        for group_name, registers in groups.items():
            # Identify grouped registers
            output = [r for r in registers if not isinstance(r["offset"], tuple)]
            special = [r for r in registers if isinstance(r["offset"], tuple)]

            if len(special) != 0:
                # Sort by variable component then by offset
                special = sorted(special, key=lambda reg: (*reg["offset"][1:], reg["offset"][0]))

                # Group the registers with common offset functions together as they will be a group
                for offset, regs in groupby(special, key=lambda reg: reg["offset"][1:]):
                    regs = list(regs)

                    # If any of the dimensions has a size of 0x04 it's an array
                    if any(o[0] == 0x04 for o in offset):

                        # Each of these will be an array on their own even if they match others
                        for r in regs:
                            base = r["offset"][0]

                            output.append(
                                {
                                    # Base register information
                                    **r,
                                    # Remove the symbols from the name then strip underscores
                                    "name": r["name"].translate({ord(o[2][0]): "" for o in offset}).strip("_"),
                                    # Offset of the smallest value in the range along with the base offset
                                    "offset": base + sum(o[0] * (o[2][1] - (1 if "-1" in o[1] else 0)) for o in offset),
                                    # Number of elements in each dimension
                                    "array": [o[2][2] - o[2][1] + 1 for o in offset],
                                }
                            )

                    # The elements form a repeated structure pattern
                    else:
                        o = offset[0]
                        # The smallest base offset to align the new struct
                        zero = min(r["offset"][0] for r in regs)
                        # The offset that this struct will be to replace
                        base = zero - o[0] * (o[2][1] - (1 if "-1" in o[1] else 0))
                        # The number of repeats of this register group
                        array = [o[2][2] - o[2][1] + 1 for o in offset]
                        # How big the group is
                        size = o[0]

                        # Update the registers to be in the new group
                        for r in regs:
                            # Zero the offset for the new register group
                            r["offset"] = r["offset"][0] - zero
                            # Strip out the symbol from the name
                            r["name"] = r["name"].translate({ord(o[2][0]): "" for o in offset}).strip("_")
                            # TODO you just removed the information you could use to validate the offset of the subfields from the main field
                            # TODO put that information back on here somewhere so that you can work out where it should be in the main group

                        new_group_name = get_group_name(regs)

                        # Create a field that references the new group
                        output.append(
                            {
                                "name": new_group_name,
                                "description": f"{new_group_name.title()} registers for {peripheral_name}",
                                "type": new_group_name,
                                "size": size,
                                "offset": base,
                                "array": array,
                            }
                        )

                        # Add an update to create a new group with these registers and the calculated name
                        updates.append((peripheral_name, new_group_name, regs))

            registers[:] = sorted(
                output,
                key=lambda reg: reg["offset"][0] if isinstance(reg["offset"], tuple) else reg["offset"],
            )

    for k1, k2, v in updates:
        peripherals[k1][k2] = v
