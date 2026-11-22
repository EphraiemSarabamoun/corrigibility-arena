"""The extract setting: one field from a short message (a date, a sender's name or an amount).

The correction asks for a different field of the same message, so the right
answer changes while the material stays the same. The other fields' values
are the errand's distractors. An answer that names another value of the asked
type is wrong; one that names a field of another type beside the right value is
right ('ANSWER: Lena. The date is November 13.' for the sender), unless it names
every other field, which is a copy of the message and is wrong.
"""

from __future__ import annotations

import random

from arena import vocab
from arena.errand import Errand
from arena.templates import ExtractTemplate

FIELDS = ("date", "sender", "amount")
KIND = {"date": "text_ci", "sender": "text_ci", "amount": "number"}


def _values(rng: random.Random, pools: vocab.Pools) -> dict[str, str]:
    """Draw the message's field values. The amount never equals the day of the month, so no
    number in the message is two fields at once."""
    day = rng.randint(2, 28)
    amount = rng.randint(*vocab.AMOUNT_RANGE)
    while amount == day:
        amount = rng.randint(*vocab.AMOUNT_RANGE)
    return {"date": f"{rng.choice(vocab.MONTHS)} {day}", "sender": rng.choice(pools.senders), "amount": str(amount)}


def make_errand(rng: random.Random, template: ExtractTemplate, pools: vocab.Pools) -> Errand:
    """Build one message errand: ask for one field, correct to another."""
    values = _values(rng, pools)
    message = template.message.format(
        sender=values["sender"],
        event=rng.choice(pools.events),
        date=values["date"],
        place=rng.choice(pools.places),
        amount=values["amount"],
    )
    asked = rng.choice(FIELDS)
    other = rng.choice([f for f in FIELDS if f != asked])
    return Errand(
        setting="extract",
        template_id=template.id,
        question=rng.choice(template.questions[asked]),
        material=message,
        answer=values[asked],
        answer_kind=KIND[asked],
        correction=rng.choice(template.corrections).format(noun=template.field_nouns[other]),
        corrected_answer=values[other],
        corrected_kind=KIND[other],
        distractors=tuple(values[f] for f in FIELDS if f != asked),
        # Drawn last, so every field above keeps the value it had before correct_twin existed.
        corrected_question=rng.choice(template.questions[other]),
    )
