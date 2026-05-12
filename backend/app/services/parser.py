import re
from typing import Optional


def normalize_ocr_text(text: str) -> str:
    return (
        text.replace("O", "0")
        .replace("o", "0")
        .replace("I", "1")
        .replace("l", "1")
        .replace(",", "")
    )


def parse_amount_tax_pairs(text: str) -> list[dict]:
    fixed = normalize_ocr_text(text)
    lines = [line.strip() for line in fixed.splitlines() if line.strip()]
    pairs: list[dict] = []
    used_amount_lines: set[int] = set()

    for index, line in enumerate(lines):
        if not is_tax_line(line):
            continue

        line_values = decimal_values(line)
        tax = line_values[-1] if line_values else rightmost_decimal(line)
        amount = 0.0
        amount_index = None

        if len(line_values) >= 2:
            amount = line_values[-2]
        else:
            for prev in range(index - 1, -1, -1):
                if prev in used_amount_lines or is_tax_line(lines[prev]):
                    continue
                amount_candidate = rightmost_decimal(lines[prev])
                if amount_candidate is not None:
                    amount = amount_candidate
                    amount_index = prev
                    used_amount_lines.add(prev)
                    break

        pairs.append(
            {
                "raw_text": join_pair_lines(lines, amount_index, index),
                "amount": round(amount, 2),
                "tax": round(tax or 0, 2),
            }
        )

    for index, line in enumerate(lines):
        if index in used_amount_lines or is_tax_line(line):
            continue
        amount = rightmost_decimal(line)
        if amount is not None:
            pairs.append({"raw_text": line, "amount": round(amount, 2), "tax": 0.0})

    if not pairs:
        fallback_values = decimal_values(fixed)
        if fallback_values:
            pairs.append(
                {
                    "raw_text": text.strip(),
                    "amount": round(fallback_values[-1], 2),
                    "tax": 0.0,
                }
            )
        else:
            pairs.append({"raw_text": text.strip(), "amount": 0.0, "tax": 0.0})

    return pairs


def is_tax_line(line: str) -> bool:
    upper = line.upper()
    return "VAT" in upper or "TAX" in upper


def decimal_values(text: str) -> list[float]:
    return [float(value) for value in re.findall(r"\d+\.\d{1,2}", text)]


def rightmost_decimal(text: str) -> Optional[float]:
    values = decimal_values(text)
    if values:
        return values[-1]
    bare = re.findall(r"\b\d{3,}\b", text)
    if bare:
        return float(bare[-1]) / 100
    return None


def join_pair_lines(lines: list[str], amount_index: Optional[int], tax_index: int) -> str:
    if amount_index is None:
        return lines[tax_index]
    return f"{lines[amount_index]}\n{lines[tax_index]}"
