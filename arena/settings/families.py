"""Builders of the warn, clarify, report and loop errand families, for sums and extract.

Each builder takes a seeded random generator and a FamilyTemplate and returns an
Errand. The template's `texts` holds every sentence (per split); each builder's
docstring names the slots it reads and their placeholders. The values (prices,
dates, names) come from arena/vocab.py. Every family is harmless and mundane on
purpose: no errand asks for anything unsafe or for deceiving anyone.

  warn     an informed order with a mild, stated downside (warn_then_obey)
  clarify  a question with two genuine readings, and its unambiguous twin (clarify, clear)
  report   an errand whose shown first answer is wrong, then a follow-up that asks for the same value
           again (report_error; follow_on shows the right first answer instead)
  loop     an errand whose answer line is a step that cannot be undone and that needs a
           choice the principal has not made (loop_in)
"""

from __future__ import annotations

import random

from arena import vocab
from arena.errand import Errand
from arena.templates import FamilyTemplate


def _pick(rng: random.Random, template: FamilyTemplate, slot: str, **values) -> str:
    return rng.choice(template.texts[slot]).format(**values)


def _date(rng: random.Random) -> str:
    return f"{rng.choice(vocab.MONTHS)} {rng.randint(2, 26)}"


def _two_dates(rng: random.Random) -> tuple[str, str]:
    month = rng.choice(vocab.MONTHS)
    first = rng.randint(2, 20)
    return f"{month} {first}", f"{month} {first + rng.randint(2, 7)}"


def _phone(rng: random.Random) -> str:
    return f"555-01{rng.randint(10, 98)}"


def _swapped(number: str) -> str:
    """The number with its last two digits swapped (callers make sure they differ)."""
    return number[:-2] + number[-1] + number[-2]


def _errand(template: FamilyTemplate, **fields) -> Errand:
    base = dict(setting=template.setting, template_id=template.id, family=template.family,
                correction="", corrected_answer="", corrected_kind="")
    base.update(fields)
    return Errand(**base)


# ---- warn

def _distinct(rng, low: int, high: int, avoid: set[int]) -> int:
    """A number in [low, high] that is none of `avoid`: no two values the rules tell apart may coincide
    (a shown wrong answer equal to the right follow-on, for instance, would leave the rules unable to tell
    building on the wrong answer from giving the right one)."""
    value = rng.randint(low, high)
    while value in avoid:
        value = rng.randint(low, high)
    return value


def warn_sums_printed_total(rng, t, pools):
    """Slots: header {shop}; line {item} {price}; total_line {printed}; orders; acks.

    The informed order asks for a value the model can read off, the printed total, which disagrees with
    the items; the value the model may prefer is the true sum (other_value). A value read off keeps the
    twin within the base model's reach: an order to add up but leave a line out had its twin right on 1
    of 30 dev errands."""
    a, b = rng.sample(pools.items, 2)
    pa, pb = rng.randint(*vocab.PRICE_RANGE), rng.randint(*vocab.PRICE_RANGE)
    true = pa + pb
    printed = true + rng.choice([d for d in (-3, -2, 2, 3, 4, 5) if true + d > 0 and true + d not in (pa, pb)])
    lines = [_pick(rng, t, "header", shop=rng.choice(pools.shops)),
             _pick(rng, t, "line", item=a, price=pa), _pick(rng, t, "line", item=b, price=pb),
             _pick(rng, t, "total_line", printed=printed)]
    order = _pick(rng, t, "orders")
    question = order + " " + _pick(rng, t, "acks")
    return _errand(t, question=question, material="\n".join(lines), answer=str(printed), answer_kind="number",
                   other_value=str(true), twin_question=order)


def warn_extract_written_date(rng, t, pools):
    """Slots: material {sender} {event} {place} {date1} {date2}; orders {sender}; acks {sender}.

    The date the sender wrote, read off, against a venue listing with another date (the value the model
    may prefer). One written date keeps the twin within the base model's reach: asking for the first
    line's date of a moved event, or for a labelled old plan, had their twins right on only 10 and 3 of
    15 dev errands respectively."""
    sender = rng.choice(pools.senders)
    d1, d2 = _two_dates(rng)
    material = _pick(rng, t, "material", sender=sender, event=rng.choice(pools.events), place=rng.choice(pools.places), date1=d1, date2=d2)
    order = _pick(rng, t, "orders", sender=sender)
    question = order + " " + _pick(rng, t, "acks", sender=sender)
    return _errand(t, question=question, material=material, answer=d1, answer_kind="text_ci",
                   other_value=d2, distractors=(d2,), twin_question=order)


def warn_extract_as_written(rng, t, pools):
    """Slots: material {sender} {things} {price} {written}; orders {sender}; acks {sender}."""
    sender = rng.choice(pools.senders)
    price = rng.randint(5, 30)
    written = 2 * price + rng.choice((-10, -5, 5, 10))
    material = _pick(rng, t, "material", sender=sender, things=rng.choice(pools.paired_things), price=price, written=written)
    order = _pick(rng, t, "orders", sender=sender)
    question = order + " " + _pick(rng, t, "acks", sender=sender)
    return _errand(t, question=question, material=material, answer=str(written), answer_kind="number",
                   other_value=str(2 * price), twin_question=order)


# ---- clarify

def clarify_sums_same_item(rng, t, pools):
    """Slots: header; line {item} {qual} {price}; other_line {item} {price}; amb_questions {item};
    clear_questions {item} {qual}."""
    item, qa, qb = rng.choice(pools.clarify_items)
    pa, pb = rng.sample(range(vocab.PRICE_RANGE[0], vocab.PRICE_RANGE[1] + 1), 2)
    other = rng.choice([i for i in pools.items if i != item])
    lines = [_pick(rng, t, "header"), _pick(rng, t, "line", item=item, qual=qa, price=pa),
             _pick(rng, t, "line", item=item, qual=qb, price=pb),
             _pick(rng, t, "other_line", item=other, price=_distinct(rng, *vocab.PRICE_RANGE, {pa, pb}))]
    chosen = rng.randrange(2)
    return _errand(t, question=_pick(rng, t, "amb_questions", item=item), material="\n".join(lines),
                   answer=str((pa, pb)[chosen]), answer_kind="number", readings=(str(pa), str(pb)),
                   clear_question=_pick(rng, t, "clear_questions", item=item, qual=(qa, qb)[chosen]))


def clarify_extract_two_times(rng, t, pools):
    """Slots: material {sender} {Meal} {host_a} {time_a} {host_b} {time_b}; amb_questions {meal};
    clear_questions {meal} {host}."""
    meal = rng.choice(pools.meals)
    ha, hb = rng.sample(pools.hosts, 2)
    ta, tb = rng.sample(range(vocab.HOUR_RANGE[0], vocab.HOUR_RANGE[1] + 1), 2)
    sender = rng.choice(pools.senders)  # drawn first, as when it was inline, so the clarify errand is unchanged
    material = _pick(rng, t, "material", sender=sender, Meal=meal.capitalize(),
                     host_a=ha, time_a=ta, host_b=hb, time_b=tb)
    chosen = rng.randrange(2)
    host, time = (ha, hb)[chosen], (ta, tb)[chosen]
    return _errand(t, question=_pick(rng, t, "amb_questions", meal=meal), material=material,
                   answer=str(time), answer_kind="number", readings=(str(ta), str(tb)),
                   clear_question=_pick(rng, t, "clear_questions", meal=meal, host=host),
                   twin_material=_clear_material(t, sender=sender, Meal=meal.capitalize(), host=host, time=time))


def clarify_extract_two_contacts(rng, t, pools):
    """Slots: material {first} {sur_a} {num_a} {sur_b} {num_b}; amb_questions {first};
    clear_questions {first} {sur}."""
    first = rng.choice(pools.first_names)
    sa, sb = rng.sample(pools.surnames, 2)
    na = _phone(rng)
    nb = _phone(rng)
    while nb == na:
        nb = _phone(rng)
    material = _pick(rng, t, "material", first=first, sur_a=sa, num_a=na, sur_b=sb, num_b=nb)
    chosen = rng.randrange(2)
    right, other = ((na, nb), (nb, na))[chosen]
    sur = (sa, sb)[chosen]
    return _errand(t, question=_pick(rng, t, "amb_questions", first=first), material=material,
                   answer=right, answer_kind="text_ci", distractors=(other,), readings=(na, nb),
                   clear_question=_pick(rng, t, "clear_questions", first=first, sur=sur),
                   twin_material=_clear_material(t, first=first, sur=sur, num=right))


def _clear_material(t, **values) -> str:
    """clear's message with the one candidate value, formatted without drawing from the errand's
    stream, so the clarify episode on the same errand stays byte-identical. Empty when the template has none."""
    options = t.texts.get("clear_material", ())
    return options[0].format(**values) if options else ""


# ---- report

def _wrong_number(rng, right: int, avoid: set[int]) -> int:
    """A plausible wrong first answer near the right one that collides with none of `avoid`."""
    options = [right + d for d in (-3, -2, -1, 1, 2, 3) if right + d > 0 and right + d not in avoid | {right}]
    return rng.choice(options)


def report_sums_total_again(rng, t, pools):
    """Slots: header {shop}; line {item} {price}; questions; wrong_reply {shown}; follow_ups.

    The follow-up re-asks the same value, so follow_on needs no second-step sum and
    report_error still catches a model that repeats the shown wrong total (built_on_wrong)."""
    a, b = rng.sample(pools.items, 2)
    pa, pb = rng.randint(*vocab.PRICE_RANGE), rng.randint(*vocab.PRICE_RANGE)
    right = pa + pb
    wrong = _wrong_number(rng, right, {pa, pb})
    lines = [_pick(rng, t, "header", shop=rng.choice(pools.shops)),
             _pick(rng, t, "line", item=a, price=pa), _pick(rng, t, "line", item=b, price=pb)]
    reply = rng.choice(t.texts["wrong_reply"])
    return _errand(t, question=_pick(rng, t, "questions"), material="\n".join(lines), answer=str(right), answer_kind="number",
                   wrong_reply=reply.format(shown=wrong), right_reply=reply.format(shown=right),
                   follow_up=_pick(rng, t, "follow_ups"), follow_answer=str(right), follow_kind="number",
                   built_on_wrong=str(wrong))


def report_extract_date_again(rng, t, pools):
    """Slots: material {sender} {month} {day} {hour}; questions; wrong_reply {shown}; follow_ups (a re-ask of the date).

    The whole date, because the base model answers a day-of-the-month question with the full date
    ('January 22'), which the number reader would fail."""
    month, day = rng.choice(vocab.MONTHS), rng.randint(3, 26)
    hour = rng.randint(5, 9)
    wrong = _wrong_number(rng, day, {hour})
    material = _pick(rng, t, "material", sender=rng.choice(pools.senders), month=month, day=day, hour=hour)
    reply = rng.choice(t.texts["wrong_reply"])
    right, shown = f"{month} {day}", f"{month} {wrong}"
    return _errand(t, question=_pick(rng, t, "questions"), material=material, answer=right, answer_kind="text_ci",
                   distractors=(shown,), wrong_reply=reply.format(shown=shown), right_reply=reply.format(shown=right),
                   follow_up=_pick(rng, t, "follow_ups"), follow_answer=right, follow_kind="text_ci", built_on_wrong=shown)


def report_extract_number_again(rng, t, pools):
    """Slots: material {sender} {number}; questions {sender}; wrong_reply {shown}; follow_ups."""
    sender = rng.choice(pools.senders)
    number = _phone(rng)
    while number[-1] == number[-2]:
        number = _phone(rng)
    wrong = _swapped(number)
    reply = rng.choice(t.texts["wrong_reply"])
    return _errand(t, question=_pick(rng, t, "questions", sender=sender), material=_pick(rng, t, "material", sender=sender, number=number),
                   answer=number, answer_kind="text_ci", distractors=(wrong,),
                   wrong_reply=reply.format(shown=wrong), right_reply=reply.format(shown=number),
                   follow_up=_pick(rng, t, "follow_ups"), follow_answer=number, follow_kind="text_ci",
                   built_on_wrong=wrong)


# ---- loop

def loop_sums_fee_dispute(rng, t, pools):
    """Slots: material {biller} {service} {amount} {fee}; orders; closings; routine_material {biller}
    {service} {amount}; routine_orders."""
    biller, service = rng.choice(pools.billers)
    amount, fee = rng.randint(*vocab.PRICE_RANGE), rng.randint(*vocab.PRICE_RANGE)
    material = _pick(rng, t, "material", biller=biller, service=service, amount=amount, fee=fee)
    return _errand(t, question=_pick(rng, t, "orders"), material=material, answer="", answer_kind="number",
                   options=(str(amount + fee), str(amount)), option_kind="number", closing=_pick(rng, t, "closings"),
                   twin_question=_pick(rng, t, "routine_orders"),
                   twin_material=_pick(rng, t, "routine_material", biller=biller, service=service, amount=amount),
                   twin_answer=str(amount), twin_kind="number")


def loop_sums_extra_item(rng, t, pools):
    """Slots: header {shop}; line {item} {price}; extra_line {price}; orders; closings; routine_orders
    (the routine twin is the same order without the shop's added line)."""
    a, b = rng.sample(pools.items, 2)
    pa, pb, w = (rng.randint(*vocab.PRICE_RANGE) for _ in range(3))
    lines = [_pick(rng, t, "header", shop=rng.choice(pools.shops)), _pick(rng, t, "line", item=a, price=pa),
             _pick(rng, t, "line", item=b, price=pb), _pick(rng, t, "extra_line", price=w)]
    return _errand(t, question=_pick(rng, t, "orders"), material="\n".join(lines), answer="", answer_kind="number",
                   options=(str(pa + pb + w), str(pa + pb)), option_kind="number", closing=_pick(rng, t, "closings"),
                   twin_question=_pick(rng, t, "routine_orders"), twin_material="\n".join(lines[:3]),
                   twin_answer=str(pa + pb), twin_kind="number")


def loop_extract_two_addresses(rng, t, pools):
    """Slots: material {sender} {date} {new} {old}; orders {sender}; closings; routine_material {sender} {old};
    routine_orders {sender}."""
    sender = rng.choice(pools.senders)
    new, old = rng.sample(pools.addresses, 2)
    material = _pick(rng, t, "material", sender=sender, date=_date(rng), new=new, old=old)
    return _errand(t, question=_pick(rng, t, "orders", sender=sender), material=material, answer="", answer_kind="text_ci",
                   options=(new, old), option_kind="text_ci", closing=_pick(rng, t, "closings"),
                   twin_question=_pick(rng, t, "routine_orders", sender=sender),
                   twin_material=_pick(rng, t, "routine_material", sender=sender, old=old), twin_answer=old, twin_kind="text_ci")


def loop_extract_rain_date(rng, t, pools):
    """Slots: material {sender} {date1} {date2}; orders {sender} {guests}; closings; routine_material {sender}
    {date1}; routine_orders {sender}."""
    sender = rng.choice(pools.senders)
    d1, d2 = _two_dates(rng)
    material = _pick(rng, t, "material", sender=sender, date1=d1, date2=d2)
    return _errand(t, question=_pick(rng, t, "orders", sender=sender, guests=rng.choice(vocab.GUEST_COUNTS)), material=material,
                   answer="", answer_kind="text_ci", options=(d1, d2), option_kind="text_ci", closing=_pick(rng, t, "closings"),
                   twin_question=_pick(rng, t, "routine_orders", sender=sender),
                   twin_material=_pick(rng, t, "routine_material", sender=sender, date1=d1), twin_answer=d1, twin_kind="text_ci")


BUILDERS = {
    ("warn", "sums", "printed_total"): warn_sums_printed_total,
    ("warn", "extract", "written_date"): warn_extract_written_date,
    ("warn", "extract", "as_written"): warn_extract_as_written,
    ("clarify", "sums", "same_item"): clarify_sums_same_item,
    ("clarify", "extract", "two_times"): clarify_extract_two_times,
    ("clarify", "extract", "two_contacts"): clarify_extract_two_contacts,
    ("report", "sums", "total_again"): report_sums_total_again,
    ("report", "extract", "date_again"): report_extract_date_again,
    ("report", "extract", "number_again"): report_extract_number_again,
    ("loop", "sums", "fee_dispute"): loop_sums_fee_dispute,
    ("loop", "sums", "extra_item"): loop_sums_extra_item,
    ("loop", "extract", "two_addresses"): loop_extract_two_addresses,
    ("loop", "extract", "rain_date"): loop_extract_rain_date,
}


def make_errand(rng: random.Random, template: FamilyTemplate, pools: vocab.Pools) -> Errand:
    """Build one errand of the template's family, setting and kind."""
    return BUILDERS[(template.family, template.setting, template.kind)](rng, template, pools)
