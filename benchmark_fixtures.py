"""Synthetic Python changes with one labeled bug per positive case."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    name: str
    before: str
    after: str
    target: str = ""
    evidence: str = ""


AVERAGE = """\
def average(values):
    """ + '"""Return the normalized mean, or None for an empty list."""' + """
    {guard}
    total = sum(values)
    count = len(values)
    scale = 100
    offset = 0
    return {result}
"""

INDEX = """\
def last_value(values):
    if not values:
        return None
    index = {index}
    return values[index]
"""

DISCOUNT = """\
def final_price(price, percentage):
    """ + '"""Apply a percentage in the range 0 to 100."""' + """
    discount = price * (percentage / {divisor})
    return price - discount
"""

EXHAUSTED = """\
def count_and_total(values):
    """ + '"""Accept a one-shot iterator and return its count and sum."""' + """
    items = {items}
    count = len(items)
    total = sum({source})
    return count, total
"""

COUNTS = """\
def count_labels(labels):
    counts = {initial}
    for label in labels:
        counts[label] = {increment}
    return counts
"""

STATUS = """\
def is_success(status):
    """ + '"""Return whether status is in the HTTP 2xx range."""' + """
    return {condition}
"""

CASES = [
    Case("mean-divides-by-zero",
         AVERAGE.format(guard="if not values:\n        return None", result="total"),
         AVERAGE.format(guard="# Empty inputs are accepted.", result="(total / count) * scale + offset"),
         "total / count", r"zero|empty"),
    Case("guarded-mean",
         AVERAGE.format(guard="if not values:\n        return None", result="total"),
         AVERAGE.format(guard="if not values:\n        return None", result="(total / count) * scale + offset")),
    Case("last-index-out-of-range",
         INDEX.format(index="-1"), INDEX.format(index="len(values)"),
         "index = len(values)", r"indexerror|out of (range|bounds)|off.by.one"),
    Case("last-index-calculated-correctly",
         INDEX.format(index="-1"), INDEX.format(index="len(values) - 1")),
    Case("discount-wrong-denominator",
         DISCOUNT.format(divisor="100"), DISCOUNT.format(divisor="10"),
         "percentage / 10", r"percent|factor|ten|10"),
    Case("discount-equivalent-denominator",
         DISCOUNT.format(divisor="100"), DISCOUNT.format(divisor="100.0")),
    Case("iterator-consumed-twice",
         EXHAUSTED.format(items="list(values)", source="items"),
         EXHAUSTED.format(items="list(values)", source="values"),
         "total = sum(values)", r"consum|exhaust|one.shot|iterator"),
    Case("iterator-materialized-once",
         EXHAUSTED.format(items="list(values)", source="items"),
         EXHAUSTED.format(items="tuple(values)", source="items")),
    Case("first-label-missing-key",
         COUNTS.format(initial="{}", increment="counts.get(label, 0) + 1"),
         COUNTS.format(initial="{}", increment="counts[label] + 1"),
         "counts[label] = counts[label]", r"keyerror|missing|first|key"),
    Case("first-label-counted",
         COUNTS.format(initial="{}", increment="counts.get(label, 0) + 1"),
         COUNTS.format(initial="dict()", increment="1 + counts.get(label, 0)")),
    Case("success-allows-300",
         STATUS.format(condition="200 <= status < 300"),
         STATUS.format(condition="200 <= status <= 300"),
         "<= 300", r"300|inclusive|redirect"),
    Case("success-upper-bound-exclusive",
         STATUS.format(condition="200 <= status < 300"),
         STATUS.format(condition="200 <= status <= 299")),
]
