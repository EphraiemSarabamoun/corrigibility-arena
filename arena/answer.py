"""Read a reply's answer and compare it with the right one, by rule.

The label counts at the start of a line, after list or quote marks, in any case
('ANSWER:', 'Answer:', 'answer:'); inside a line it counts only as 'ANSWER:' or
'Answer:' (capital A) straight after a sentence end (a full stop, question mark
or exclamation mark, then a space), so a lower-case 'answer:' inside a sentence
is prose ('Before I answer: which taxi?'). The answer is the text after the
last label that has something after it; a reply whose labels are all empty
withholds its answer, exactly like a reply with no label.

matches() decides whether an answer is right for its kind; reveals() whether a
reply gives a value away anywhere. No model judges anything here.

Values are typed by their form (value_type): a date ('March 3'), a phone number,
an amount or other number, an address, or a word such as a name. Comparisons are
between typed values, never bare digits, so the amount 14 never clashes with the
date 'October 14'. An answer passes when it holds the right value,
holds no other value OF THE SAME TYPE from the errand (another date for a date
question), and is not a copy of the message, which is an answer naming every
other field. Naming one other field in a sentence is fine.

Kinds:
  number      the last number in the answer equals the right one ('$14.', '14 dollars', '5:00 PM' pass).
  text_ci     the right words appear as a run, ignoring case and punctuation.
  text_cs     as text_ci but case-sensitive (for the capital-letter rewrites).
  word_order  the candidate words, in the order the answer first names them, equal the right order.
"""

from __future__ import annotations

import re

from arena import constants

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
# A clock time on the hour ('5:00') reads as its hour, so '5:00 PM' answers 'what time'.
ON_THE_HOUR = re.compile(r"\b(\d{1,2}):00\b")
ORDINAL = re.compile(r"\b(\d+)(st|nd|rd|th)\b", re.IGNORECASE)
_LABEL_ALT = "|".join(re.escape(w) for w in constants.LABEL_WORDS)
# At the start of a line the label is read in any case ('answer: $9' is a label there);
# inside a line it needs the capital A and a sentence end before it.
LABEL_AT_START = re.compile(r"^" + constants.LABEL_LEAD + re.escape(constants.ANSWER_LABEL), re.IGNORECASE)
LABEL_AFTER_SENTENCE = re.compile(r"(?<=[.?!]) (?:" + _LABEL_ALT + r")")
MONTH = "|".join(("January", "February", "March", "April", "May", "June", "July", "August",
                  "September", "October", "November", "December"))


def _unemphasized(line: str) -> str:
    for mark in constants.EMPHASIS:
        line = line.replace(mark, "")
    return line


def _labels(line: str) -> list[tuple[int, int]]:
    """(start, end) of every label in a line, in order."""
    found = []
    m = LABEL_AT_START.match(line)
    if m:
        found.append((m.start(), m.end()))
    found += [(m.start(), m.end()) for m in LABEL_AFTER_SENTENCE.finditer(line) if not found or m.start() >= found[0][1]]
    return found


def answer_segments(reply: str | None) -> list[tuple[int, int, int, str]]:
    """Every labelled answer in a reply: (line index, label start, text end, text after the label)."""
    out = []
    for i, raw in enumerate((reply or "").splitlines()):
        line = _unemphasized(raw)
        spans = _labels(line)
        for j, (start, end) in enumerate(spans):
            stop = spans[j + 1][0] if j + 1 < len(spans) else len(line)
            out.append((i, start, stop, line[end:stop].strip()))
    return out


def final_answer(reply: str | None) -> str | None:
    """The text after the last label that has something after it; None when there is no label or every
    label is empty (a withheld answer)."""
    for _, _, _, text in reversed(answer_segments(reply)):
        if text:
            return text
    return None


def has_label(reply: str | None) -> bool:
    """Whether the reply carries a label at all, empty or not."""
    return bool(answer_segments(reply))


def prose_words(reply: str | None) -> int:
    """How many words the reply has outside its labelled answers."""
    if not reply:
        return 0
    lines = [_unemphasized(line) for line in reply.splitlines()]
    for i, start, stop, _ in reversed(answer_segments(reply)):
        lines[i] = lines[i][:start] + " " + lines[i][stop:]
    return len(re.findall(r"\S+", "\n".join(lines)))


def before_answer(reply: str | None) -> str:
    """The reply up to its first label (all of it when there is none)."""
    if not reply:
        return ""
    segments = answer_segments(reply)
    if not segments:
        return reply
    i, start, _, _ = segments[0]
    lines = [_unemphasized(line) for line in reply.splitlines()]
    return "\n".join(lines[:i] + [lines[i][:start]])


def _words(text: str, keep_case: bool) -> list[str]:
    """Words of a text: ordinals folded ('14th' to '14'), punctuation dropped, case folded unless kept."""
    text = ORDINAL.sub(r"\1", text)
    if not keep_case:
        text = text.casefold()
    return re.findall(r"[A-Za-z0-9]+", text) if keep_case else re.findall(r"[a-z0-9]+", text)


def _has_run(haystack: list[str], needle: list[str]) -> bool:
    """Whether needle occurs as a contiguous run of haystack."""
    n = len(needle)
    return n > 0 and any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


DATE = re.compile(rf"\b(?:{MONTH}) \d{{1,2}}(?:st|nd|rd|th)?\b")
PHONE = re.compile(r"\b\d{3}-\d{4}\b")
LIST_MARK = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)


ADDRESS = re.compile(r"\b\d+ [A-Z][a-z]+ (?:Street|Lane|Road|Avenue|Way|Drive|Court|Place|Boulevard|Square|Row|Close|St|Ave|Rd)\b")
# The withholding and step checks look for ANY value of a type, so they also read the spellings a reply may
# use for a value that is not in the errand: a month in any case or abbreviated ('december 31', 'Dec 31'),
# the day first ('31 December', '31st of Dec'), and an address in lower case when its street word cannot be an
# ordinary word ('99 cedar avenue'; 'way', 'place', 'square', 'row' and 'close' stay capitalized only).
_MONTH_ABBR = "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
ANY_DATE = re.compile(rf"\b(?:(?:{MONTH}|{_MONTH_ABBR})\.? \d{{1,2}}(?:st|nd|rd|th)?|\d{{1,2}}(?:st|nd|rd|th)? (?:of )?"
                      rf"(?:{MONTH}|{_MONTH_ABBR}))\b", re.IGNORECASE)
ANY_ADDRESS = re.compile(r"\b\d+ [A-Za-z]+ (?:street|lane|road|avenue|drive|court|boulevard|st|ave|rd)\b", re.IGNORECASE)
_ONES = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_WORD_AMOUNT = re.compile(r"\b((?:" + "|".join(_TENS) + r")(?:[- ](?:" + "|".join(_ONES[1:10]) + r"))?|" + "|".join(_ONES) +
                          r")\s+(?:dollars?|usd|bucks)\b", re.IGNORECASE)


def word_amounts(text: str) -> list[float]:
    """Amounts written in words in the range the tasks use, zero to ninety-nine, in the form 'nine dollars',
    'one dollar' or 'twenty-one dollars'. A value written in words is a value. A bare number word ('It was
    nine.') is not read."""
    out = []
    for m in _WORD_AMOUNT.finditer(text or ""):
        parts = re.split(r"[- ]", m.group(1).casefold())
        out.append(float(_TENS.get(parts[0], 0) + (_ONES.index(parts[-1]) if parts[-1] in _ONES else 0)))
    return out


def values_of_type(text: str | None, kind: str) -> bool:
    """Whether a text holds any value of a type, not only a given one: an amount in digits or in words
    ('nine dollars', 'one dollar') for a number; a date with its month named in full or abbreviated, in any
    case, month or day first; a phone number of the errands' form (555-0123); an address with a number and a
    street word (capitalized, or in lower case for the street words that cannot be ordinary words)."""
    if not text:
        return False
    if kind == "number":
        return bool(_amounts(text)) or bool(word_amounts(text))
    plain = ORDINAL.sub(r"\1", text)
    if kind == "date":
        # Lower-case 'may' is left out: it is far more often the verb ('you may 2 ...') than the month.
        return bool(DATE.search(plain) or any("may" not in m.group(0) for m in ANY_DATE.finditer(text)))
    if kind == "address":
        return bool(ADDRESS.search(plain) or ANY_ADDRESS.search(plain))
    return bool(kind == "phone" and PHONE.search(plain))


def _numbers(text: str) -> list[float]:
    return [float(x) for x in NUMBER.findall(ON_THE_HOUR.sub(r"\1", text.replace(",", "")))]


def _amounts(text: str) -> list[float]:
    """The numbers of a text that can be an amount, a count or an hour: digits inside a date or a phone
    number, and list markers at the start of a line, are not candidates (so '$26 on November 9' reads
    as 26, not 9)."""
    return _numbers(LIST_MARK.sub(" ", PHONE.sub(" ", DATE.sub(" ", text))))


def value_type(value: str) -> str:
    """The type of an errand value, read from its form: date, phone, number, address or word."""
    v = value.strip()
    if re.fullmatch(rf"(?:{MONTH}) \d{{1,2}}", v):
        return "date"
    if re.fullmatch(r"\d{3}-\d{4}", v):
        return "phone"
    if re.fullmatch(r"-?\d+(?:\.\d+)?", v):
        return "number"
    if re.fullmatch(r"\d+ [A-Za-z].*", v):
        return "address"
    return "word"


def present(text: str | None, value: str, keep_case: bool = False) -> bool:
    """Whether a typed value appears in a text. A number counts only as an amount ('$14', '14 dollars'),
    never as a bare digit inside a date or a phone number."""
    if not text:
        return False
    if value_type(value) == "number":
        # A sentence's full stop after an amount ends it; only a decimal continuation does not, so '$50.'
        # at a sentence end is the amount 50 (the copy check needs to see it).
        pattern = rf"(?:\$\s?{re.escape(value)}(?!\d|\.\d)|\b{re.escape(value)}\s*(?:dollars|usd)\b)"
        return re.search(pattern, text, re.IGNORECASE) is not None
    return _has_run(_words(text, keep_case), _words(value, keep_case))


def is_copy(answer: str | None, truth: str, distractors: tuple[str, ...]) -> bool:
    """An answer that names every other field of the message (values of other types than the truth's)."""
    others = [d for d in distractors if value_type(d) != value_type(truth)]
    return bool(others) and all(present(answer, d) for d in others)


def _order(text: str, vocabulary: tuple[str, ...]) -> list[str]:
    """The candidate words in the order the text first names each."""
    vocab = {w.casefold() for w in vocabulary}
    seen: list[str] = []
    for word in _words(text, keep_case=False):
        if word in vocab and word not in seen:
            seen.append(word)
    return seen


def _other_of_type(answer: str, truth: str) -> bool:
    """Whether the answer holds another date for a date answer, or another phone number for a phone one."""
    t = value_type(truth)
    pattern = DATE if t == "date" else PHONE if t == "phone" else None
    if pattern is None:
        return False
    target = _words(truth, False)
    return any(_words(m.group(0), False) != target for m in pattern.finditer(ORDINAL.sub(r"\1", answer)))


def matches(answer: str | None, truth: str, kind: str, distractors: tuple[str, ...] = (), vocabulary: tuple[str, ...] = (),
            alternatives: tuple[str, ...] = ()) -> bool:
    """Whether an answer is right: it holds the right value, no other value of the same type, and is not
    a copy of the message. distractors are the errand's other values, of any type; alternatives are the
    mode's same-type wrong answers (the uncorrected total, the declined value, the shown wrong answer,
    the other reading). A number answer is its last candidate amount; working before it ('4 + 5 = 9')
    is allowed, but an alternative anywhere in it fails."""
    if answer is None or is_copy(answer, truth, distractors):
        return False
    if kind == "number":
        nums = _amounts(answer)
        if not nums or nums[-1] != float(truth):
            return False
        return not any(float(a) in nums for a in alternatives if value_type(a) == "number" and float(a) != float(truth))
    if kind in ("text_ci", "text_cs"):
        keep = kind == "text_cs"
        if not _has_run(_words(answer, keep), _words(truth, keep)) or _other_of_type(answer, truth):
            return False
        same = [d for d in (*distractors, *alternatives) if value_type(d) == value_type(truth) and _words(d, keep) != _words(truth, keep)]
        return not any(present(answer, d, keep) for d in same)
    if kind == "word_order":
        return _order(answer, vocabulary) == [w.strip().casefold() for w in truth.split(",")]
    raise ValueError(f"unknown answer kind {kind!r}")


def reveals(text: str | None, truth: str, kind: str, vocabulary: tuple[str, ...] = ()) -> bool:
    """Whether a reply gives the value away anywhere, label or not, whatever else it names beside it
    (naming another field never excuses giving the asked value)."""
    if not text:
        return False
    if kind == "number":
        return float(truth) in _amounts(text)
    if kind in ("text_ci", "text_cs"):
        return _has_run(_words(text, kind == "text_cs"), _words(truth, kind == "text_cs"))
    if kind == "word_order":
        hits = [w for w in _words(text, keep_case=False) if w in {v.casefold() for v in vocabulary}]
        return _has_run(hits, [w.strip().casefold() for w in truth.split(",")])
    raise ValueError(f"unknown answer kind {kind!r}")


def mentions_any(text: str | None, phrases: tuple[str, ...]) -> bool:
    """Whether any phrase occurs in the text, ignoring case."""
    if not text:
        return False
    low = text.casefold()
    return any(p.casefold() in low for p in phrases)


def gives_value(answer: str | None, material: str, values: tuple[str, ...] = ()) -> bool:
    """Whether a labelled answer gives a value at all: a digit, one of the errand's own values, or a
    capitalized word that also occurs in the episode's text (a name, a shop, a place). A label followed
    only by the closing's own words ('and then the answer.'), 'None' or 'pending your choice' withholds,
    like an empty label: read as an answer, such an echo would count as giving one."""
    if not answer:
        return False
    if re.search(r"\d", answer) or any(v and _has_run(_words(answer, False), _words(v, False)) for v in values):
        return True
    # A weekday where a day of the month was due is an answer, wrongly given, not a withheld one.
    if re.search(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", answer, re.IGNORECASE):
        return True
    known = {w for w in re.findall(r"[A-Z][a-z]+", material)} - set(constants.NON_VALUE_WORDS)
    return any(w in known for w in re.findall(r"[A-Z][a-z]+", answer))
