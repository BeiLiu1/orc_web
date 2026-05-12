import re


def fix(text):

    text = text.replace("O", "0")
    text = text.replace("o", "0")
    text = text.replace("I", "1")
    text = text.replace("l", "1")

    return text


def parse_block_amounts(text):

    text = fix(text)

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    pairs = []

    i = 0

    while i < len(lines):

        line = lines[i]

        nums = re.findall(r"\d+\.\d{1,2}", line)
        nums = [float(x) for x in nums] if nums else []

        # VAT line
        if "VAT" in line.upper():

            tax = nums[-1] if nums else 0

            # OCR missed decimal point, try bare integer and fix
            if tax == 0:
                bare = re.findall(r"\b\d{2,}\b", line)
                if bare:
                    tax = float(bare[-1]) / 100

            j = i - 1
            while j >= 0:

                prev_nums = re.findall(r"\d+\.\d{1,2}", lines[j])
                prev_nums = [float(x) for x in prev_nums] if prev_nums else []

                # Fallback: try bare integers on previous line too
                if not prev_nums:
                    bare_prev = re.findall(r"\b\d{3,}\b", lines[j])
                    if bare_prev:
                        prev_nums = [float(bare_prev[-1]) / 100]

                if prev_nums:

                    amount = prev_nums[-1]
                    pairs.append((amount, tax))
                    break

                j -= 1

            i += 1
            continue

        # Amount line
        if nums:

            amount = nums[-1]

            tax = 0

            if i + 1 < len(lines) and "VAT" in lines[i + 1].upper():

                vat_line = lines[i + 1]

                vat_nums = re.findall(r"\d+\.\d{1,2}", vat_line)
                vat_nums = [float(x) for x in vat_nums] if vat_nums else []

                tax = vat_nums[-1] if vat_nums else 0

                # Same fallback for missing decimal
                if tax == 0:
                    bare = re.findall(r"\b\d{2,}\b", vat_line)
                    if bare:
                        tax = float(bare[-1]) / 100

                pairs.append((amount, tax))

                i += 2
                continue

            pairs.append((amount, 0))

        else:

            # Amount line has no decimal matches, try bare integer fallback
            bare_amt = re.findall(r"\b\d{3,}\b", line)
            if bare_amt:
                amount = float(bare_amt[-1]) / 100

                tax = 0
                if i + 1 < len(lines) and "VAT" in lines[i + 1].upper():

                    vat_line = lines[i + 1]
                    vat_nums = re.findall(r"\d+\.\d{1,2}", vat_line)
                    vat_nums = [float(x) for x in vat_nums] if vat_nums else []

                    tax = vat_nums[-1] if vat_nums else 0

                    if tax == 0:
                        bare_vat = re.findall(r"\b\d{2,}\b", vat_line)
                        if bare_vat:
                            tax = float(bare_vat[-1]) / 100

                    pairs.append((amount, tax))
                    i += 2
                    continue

                pairs.append((amount, 0))

        i += 1

    amount_total = round(sum(p[0] for p in pairs), 2)
    tax_total = round(sum(p[1] for p in pairs), 2)

    return {
        "amount": amount_total,
        "tax": tax_total,
        "pairs": pairs
    }
