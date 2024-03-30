import re


def fields(peripheral_name, register_name, txt):

    # Split up the text for descriptions of the bits
    vs = re.split(r"Bits?([\d :\-,\[\]]+)(\w+)(?:\[(\d+:\d+)\])?\s*[\:,]", txt, flags=re.MULTILINE)
    total_size_texts = vs[1::4]
    field_names = vs[2::4]
    member_size_texts = vs[3::4]
    texts = vs[4::4]

    fields = []
    for total_text, member_text, field_name, text in zip(total_size_texts, member_size_texts, field_names, texts):

        if "x" in field_name or "y" in field_name:
            print(f"Array field found: {field_name}")
            print(f"Total: {total_text}")
            print(f"Member: {member_text}")

        # Calculate the bit mask for this register
        bits = re.findall(r"(\d+[:-]\d+|\d+)", total_text)
        mask = 0
        for bit in bits:
            if "-" in bit or ":" in bit:
                v1, v2 = re.split("[:-]", bit)
                start = min(int(v1), int(v2))
                end = max(int(v1), int(v2))
                mask |= int(2 ** (end - start + 1) - 1) << start
            else:
                mask |= 1 << int(bit)

        # Count the number of set bits in the mask
        set_bits = 0
        active_bits = mask
        while active_bits:
            set_bits += active_bits & 1
            active_bits >>= 1

        values = re.split(
            r"([01]{{{set_bits}}}|Note|0x[A-F0-9]+|Others?|Other configurations):".format(set_bits=set_bits),
            text,
            flags=re.IGNORECASE,
        )
        doc = re.sub(r"\s+", " ", values[0]).strip()
        values = [(re.sub(r"\s", "", k), re.sub(r"\s+", " ", v).strip()) for k, v in zip(values[1::2], values[2::2])]

        # Add the field to the peripheral
        fields.append(
            {
                "name": field_name,
                "description": " ".join([doc, *[v for k, v in values if k == "Note"]]),
                "values": [(k, v) for k, v in values if k != "Note"],
                "mask": bin(mask),
            }
        )

    return fields
