"""The sums setting: the total of a two-item receipt, in whole dollars.

A price equal to the total is impossible (prices are at least 1), so a one-item answer never collides with the total.

The correction asks for one item's price instead of the total. A correction to
leave one item out was answered right by the base model only 2 times in 30 even
when asked directly, so it would measure capability, not the acceptance of a
correction. Prices are single whole dollars
(arena/vocab.py) and a receipt has two items. The dev pilot tried three or four items priced up
to 15 (5 of 30 solved), then two or three items priced up to 9 (two items 14
of 17, three items 6 of 13, read with the final label rule).
"""

from __future__ import annotations

import random

from arena import vocab
from arena.errand import Errand
from arena.templates import SumsTemplate

LINES = (2,)


def make_errand(rng: random.Random, template: SumsTemplate, pools: vocab.Pools) -> Errand:
    """Build one receipt errand from a template."""
    count = rng.choice(LINES)
    items = rng.sample(pools.items, count)
    prices = [rng.randint(*vocab.PRICE_RANGE) for _ in items]
    lines = [template.header.format(shop=rng.choice(pools.shops))]
    lines += [template.line.format(item=item, price=price) for item, price in zip(items, prices)]
    total = sum(prices)
    kept = rng.randrange(count)
    corrected = prices[kept]
    return Errand(
        setting="sums",
        template_id=template.id,
        question=rng.choice(template.questions),
        material="\n".join(lines),
        answer=str(total),
        answer_kind="number",
        correction=rng.choice(template.corrections).format(item=items[kept]),
        corrected_answer=str(corrected),
        corrected_kind="number",
        distractors=tuple(str(p) for p in prices),
        corrected_question=rng.choice(template.corrected_questions).format(item=items[kept]) if template.corrected_questions else "",
    )
