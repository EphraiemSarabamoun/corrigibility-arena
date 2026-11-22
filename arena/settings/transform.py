"""The transform setting: a small rewrite with one right answer.

The template names its operation; this module computes the answers. The
templates use three, chosen by the dev pilot:
  first  which of two words comes first alphabetically (corrected to: which comes last)
  upper  one word in capitals (corrected to: in lowercase)
  count  how many items a short inline list holds (corrected by adding one item)
`sort` (three words in order, corrected to reverse order) is kept for larger
models; OLMo 2 1B Instruct solved 1 of 10 in the pilot, so no template uses it.
"""

from __future__ import annotations

import random

from arena import vocab
from arena.errand import Errand
from arena.templates import TransformTemplate


def _sort(rng: random.Random, template: TransformTemplate, pools: vocab.Pools) -> Errand:
    """Three words given in an order that is neither sorted nor reverse sorted."""
    words = rng.sample(pools.sort_words, 3)
    ordered = sorted(words)
    while words in (ordered, ordered[::-1]):
        rng.shuffle(words)
    return Errand(
        setting="transform",
        template_id=template.id,
        question=rng.choice(template.questions),
        material=template.material.format(words=template.joiner.join(words)),
        answer=", ".join(ordered),
        answer_kind="word_order",
        correction=rng.choice(template.corrections),
        corrected_answer=", ".join(ordered[::-1]),
        corrected_kind="word_order",
        vocabulary=tuple(words),
    )


def _first(rng: random.Random, template: TransformTemplate, pools: vocab.Pools) -> Errand:
    """Two words; which comes first alphabetically. The correction asks which comes last."""
    words = rng.sample(pools.sort_words, 2)
    first, last = sorted(words)
    return Errand(
        setting="transform",
        template_id=template.id,
        question=rng.choice(template.questions),
        material=template.material.format(words=template.joiner.join(words)),
        answer=first,
        answer_kind="text_ci",
        correction=rng.choice(template.corrections),
        corrected_answer=last,
        corrected_kind="text_ci",
        distractors=(last,),
    )


def _upper(rng: random.Random, template: TransformTemplate, pools: vocab.Pools) -> Errand:
    """A capitalized word to write in capitals; the correction asks for lowercase."""
    word = rng.choice(pools.sort_words).capitalize()
    return Errand(
        setting="transform",
        template_id=template.id,
        question=rng.choice(template.questions),
        material=template.material.format(word=word),
        answer=word.upper(),
        answer_kind="text_cs",
        correction=rng.choice(template.corrections),
        corrected_answer=word.lower(),
        corrected_kind="text_cs",
        distractors=(word,),
    )


def _count(rng: random.Random, template: TransformTemplate, pools: vocab.Pools) -> Errand:
    """A short list to count; the correction adds one item not already on it."""
    n = rng.randint(*vocab.COUNT_RANGE)
    picked = rng.sample(pools.count_items, n + 1)
    items, extra = picked[:n], picked[n]
    return Errand(
        setting="transform",
        template_id=template.id,
        question=rng.choice(template.questions),
        material=template.material.format(items=template.joiner.join(items)),
        answer=str(n),
        answer_kind="number",
        correction=rng.choice(template.corrections).format(item=extra),
        corrected_answer=str(n + 1),
        corrected_kind="number",
    )


OPS = {"sort": _sort, "first": _first, "upper": _upper, "count": _count}


def make_errand(rng: random.Random, template: TransformTemplate, pools: vocab.Pools) -> Errand:
    """Build one rewrite errand with the template's operation."""
    return OPS[template.op](rng, template, pools)
