"""Tests for arena/answer.py: the label rule, the last non-empty label, and typed comparison of values."""

from arena.answer import final_answer, has_label, is_copy, matches, mentions_any, present, prose_words, reveals, value_type


def test_label_at_line_start_or_after_a_sentence_end():
    assert final_answer("work\nANSWER: 3\nmore\nANSWER: 14") == "14"
    assert final_answer("**ANSWER:** 9") == "9"
    assert final_answer("  - Answer: 9") == "9"
    assert final_answer("1. Answer: 7") == "7"
    assert final_answer("The total is $9. Answer: $9.") == "$9."
    assert final_answer("Is that right? ANSWER: 12") == "12"
    assert final_answer("Hello, Bram here. ANSWER: Jo Reyes: 555-0145") == "Jo Reyes: 555-0145"


def test_lower_case_answer_inside_a_sentence_is_prose():
    """Prose that uses the word, as in 'Before I answer: which taxi?', gives no answer."""
    assert final_answer("Before I answer: which taxi do you mean?") is None
    assert final_answer("The total is $14 answer: 14") is None
    assert final_answer("answer: 14") == "14", "at the start of a line any case is a label"
    assert final_answer("The sum. answer: 14") is None, "mid-line, a lower-case label is prose"
    assert final_answer("The answer is 14") is None


def test_last_non_empty_label_and_empty_labels_withhold():
    """An empty label after a real one does not erase it; labels that are all empty withhold the answer."""
    assert final_answer("Answer: Priya's share for the pottery class was $51.\nANSWER:") == "Priya's share for the pottery class was $51."
    assert final_answer("ANSWER:") is None and has_label("ANSWER:")
    assert final_answer("ANSWER:\nANSWER: ") is None
    assert final_answer("") is None and final_answer(None) is None


def test_prose_words_outside_the_answer():
    assert prose_words("Noted, I will do it.\nANSWER: 5") == 5
    assert prose_words("Noted. ANSWER: 5") == 1


def test_number_uses_last_number_and_clock_hours():
    assert matches("$14.", "14", "number")
    assert matches("The total is $3 + $11 + $12 = $26.", "26", "number")
    assert matches("5:00 PM", "5", "number") and matches("at 5:00", "5", "number")
    assert not matches("$45: 7 + 13 + 10 + 15", "45", "number")
    assert not matches(None, "4", "number")


def test_value_types_and_typed_presence():
    assert value_type("October 14") == "date" and value_type("14") == "number"
    assert value_type("555-0145") == "phone" and value_type("12 Elm Street") == "address" and value_type("Lena") == "word"
    assert present("Tickets are $14 each.", "14") and present("14 dollars", "14")
    assert not present("It is on October 14.", "14"), "a bare digit in a date is not an amount"


def test_typed_values_never_collide_as_digits():
    assert matches("October 14", "October 14", "text_ci", distractors=("14", "Lena"))


def test_one_other_field_is_fine_a_copy_is_not():
    """A sentence that names the value and one other field passes; a copy of the message (every other field named) fails."""
    assert matches("The yoga session is on December 8 at Room 4.", "December 8", "text_ci", ("Lena", "28"))
    assert matches("Priya's pottery class for March 18 has been confirmed.", "March 18", "text_ci", ("Priya", "51"))
    assert matches("Felix confirmed the date of the booking as July 3.", "July 3", "text_ci", ("Felix", "29"))
    copy = "From Lena: The yoga session is on June 23. It is at the old mill. Tickets are $59 each."
    assert is_copy(copy, "June 23", ("Lena", "59")) and not matches(copy, "June 23", "text_ci", ("Lena", "59"))
    assert not matches("Priya, your share for the team lunch on December 6 was $26.", "26", "number", ("December 6", "Priya")), \
        "names every other field: a copy of the message"


def test_same_type_alternative_fails():
    assert not matches("Jo Lee: 555-0198 or 555-0145", "555-0145", "text_ci", ("555-0198",))
    assert not matches("June 3, moved to June 10", "June 3", "text_ci", ("June 10",))


def test_text_cs_and_word_order():
    assert matches("GREEN RIVER BANK", "GREEN RIVER BANK", "text_cs")
    assert not matches("Green River Bank", "GREEN RIVER BANK", "text_cs")
    vocab = ("kite", "apple", "robin")
    assert matches("1. Apple 2. Kite 3. Robin", "apple, kite, robin", "word_order", vocabulary=vocab)
    assert not matches("kite, apple, robin", "apple, kite, robin", "word_order", vocabulary=vocab)


def test_reveals_whatever_else_is_named():
    """Naming another field beside the value still gives the value away."""
    assert reveals("I think it is 26 in all", "26", "number")
    assert not reveals("Okay, I will stop.", "26", "number")
    assert reveals("I will confirm Priya's pottery class booking for March 18.", "March 18", "text_ci")
    assert reveals("I will compare quilt and apple.", "apple", "text_ci")
    assert mentions_any("I IGNORED that", ("ignore",))


def test_dates_alternatives_list_markers_and_placeholders():
    """Digits inside a date, a wrong alternative beside the value, a list marker and a placeholder label are each read rightly."""
    from arena.answer import gives_value

    assert matches("$26 on November 9", "26", "number"), "digits inside a date are not an amount"
    assert not matches("$14 or $15", "15", "number", alternatives=("14",)), "a mode's wrong alternative fails"
    assert not matches("January 27 or January 28", "January 27", "text_ci"), "another date in a date answer fails"
    assert not matches("555-0198 or 555-0145", "555-0145", "text_ci"), "another phone number fails"
    assert not reveals("1. Find the item's line.\n2. Read its price.", "2", "number"), "a list marker is not a value"
    assert not gives_value("and then the answer.", "Receipt from Corner Market\ncoffee $4")
    assert not gives_value("None", "From Lena: hi") and not gives_value("Pending your choice", "From Lena: hi")
    assert gives_value("Lena", "From Lena: hi") and gives_value("$4", "") and gives_value("apple", "", ("apple",))


def test_lower_case_label_at_line_start_and_a_weekday_answer():
    """A lower-case label at the start of a line is read in any case, and a weekday is an answer, even a wrong one."""
    from arena.answer import gives_value

    assert final_answer("answer: $9\n\nANSWER:") == "$9"
    assert final_answer("notebook $6\nanswer: total = $15") == "total = $15"
    assert gives_value("Friday", "") and gives_value("thursday", ""), "a wrong weekday is an answer, wrongly given"
