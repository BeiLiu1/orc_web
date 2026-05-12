from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


def money(value: Optional[Union[float, int]]) -> float:
    return round(float(value or 0), 2)


def formula(values: list[float]) -> str:
    usable = [money(v) for v in values if money(v) != 0]
    if not usable:
        return "0.00"
    return " + ".join(f"{v:.2f}" for v in usable)


@dataclass
class GroupTotals:
    amount_total: float = 0
    tax_total: float = 0
    formula_amount: str = "0.00"
    formula_tax: str = "0.00"


@dataclass
class JobTotals:
    amount_total: float = 0
    tax_total: float = 0
    groups: dict[str, GroupTotals] = field(default_factory=dict)


def calculate_group(items: list[dict]) -> GroupTotals:
    amounts = [money(item.get("amount")) for item in items]
    taxes = [money(item.get("tax")) for item in items]
    return GroupTotals(
        amount_total=money(sum(amounts)),
        tax_total=money(sum(taxes)),
        formula_amount=formula(amounts),
        formula_tax=formula(taxes),
    )
