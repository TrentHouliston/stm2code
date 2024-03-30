import pypdf
import re


def find_limits(pdf, items, level=0):
    sections = []
    prev = []
    for item in items:
        if isinstance(item, list):
            sub_sections, last = find_limits(pdf, item, level + 1)
            prev.extend(last)
            sections.extend(sub_sections)
        else:
            start = (pdf.get_destination_page_number(item), item.top)
            for p in prev:
                p["end"] = start

            sections.append({"title": item.title, "level": level, "start": start})

            # People can't spell
            if sections[-1]["title"] == "53.6.5 SWPMI Interrupt Enable register (SMPMI_IER)":
                sections[-1]["title"] = "53.6.5 SWPMI Interrupt Enable register (SWPMI_IER)"

            prev = [sections[-1]]

    return sections, prev


def register_sections(pdf):

    limits, last = find_limits(pdf, pdf.outline)

    active = False
    level = 0
    for limit in limits:
        # print(limit["title"])
        if re.search(r"^\d+(?:\.\d+)+.*\sregisters.*$", limit["title"], flags=re.IGNORECASE):
            print("Searching:", limit["title"])
            level = limit["level"]
            active = True
        elif limit["level"] <= level:
            active = False

        if not active:
            continue

        # Check if the title is a register
        r = re.search(r"^[\d.]+ ([A-Z0-9_]+) (.+) \(\1([^)]*)\)", limit["title"])

        if not r:
            continue

        peripheral_name = r.group(1).strip("_ ")
        register_name = r.group(3).strip("_ ")
        register_description = re.sub(r"\s+", " ", r.group(2)).strip(" ")

        print(f"\tFound: {peripheral_name}_{register_name}")

        # False positives, RAM is actually the RAMECC that gets detected earlier in a different section
        if peripheral_name in ["RAM", "AXI"]:
            continue

        parts = []
        for i in range(limit["start"][0], limit["end"][0] + 1):

            def visitor(text, cm, tm, font_dict, font_size):
                ftr = 100
                hdr = 770
                y = pypdf.mult(tm, cm)[5]  # 0 is the bottom of the page
                if (
                    y > ftr
                    and y < hdr
                    and (i != limit["start"][0] or y < limit["start"][1])
                    and (i != limit["end"][0] or y > limit["end"][1])
                    and text.strip() != ""
                ):
                    parts.append(text)

            pdf.pages[i].extract_text(visitor_text=visitor)

        yield peripheral_name, register_name, register_description, "".join(parts)
