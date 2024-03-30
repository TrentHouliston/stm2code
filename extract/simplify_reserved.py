def simplify_reserved(peripherals):

    # Merge the reserved bits into a single field
    for groups in peripherals.values():
        for registers in groups.values():
            for register in registers:
                reserved = [r for r in register["fields"] if r["name"] == "Reserved"]
                register["fields"] = [r for r in register["fields"] if r["name"] != "Reserved"]
                if len(reserved) > 0:
                    register["fields"].append(
                        {
                            "name": "Reserved",
                            "description": "must be kept at reset value.",
                            "values": [],
                            "mask": bin(sum([int(r["mask"], 0) for r in reserved])),
                        }
                    )
