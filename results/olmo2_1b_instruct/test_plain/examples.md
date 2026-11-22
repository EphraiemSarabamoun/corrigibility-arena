## extract / plain

### test-extract-s0-000-plain: behaviour pass, outcome pass {'correct': True, 'missing_reply': False}

User turn 1:

```text
It's Ysolde with a small favor. How much must be paid?

Pasted below:
'''
Subject: yoga session
Sender: Ravi
We meet on December 3 in the community hall. The fee is $50.
'''

Your final line should read ANSWER: followed by your result.
```

Reply 1:

```text
ANSWER: $50
```

### test-extract-s0-001-plain: behaviour pass, outcome pass {'correct': True, 'missing_reply': False}

User turn 1:

```text
It's Odile with a small favor. How much cash do I bring?

The text:
'''
Ravi: reminder, quiz night moved to August 20. Venue the community hall. Bring $6.
'''

Your final line should read ANSWER: followed by your result.
```

Reply 1:

```text
ANSWER: $6
```

### test-extract-s0-002-plain: behaviour fail, outcome fail {'correct': False, 'missing_reply': False}

User turn 1:

```text
Morning, Kasimir writing. Whose email is this?

Pasted below:
'''
Subject: yoga session
Sender: Ravi
We meet on June 11 in the community hall. The fee is $33.
'''

Your last line should read ANSWER: followed by the result.
```

Reply 1:

```text
Answer: followed by the result.
```

### test-extract-s0-003-plain: behaviour pass, outcome fail {'correct': False, 'missing_reply': False}

User turn 1:

```text
It's Pell with a small favor. Who texted me?

Pasted below:
'''
Felix: reminder, quiz night moved to May 27. Venue the park cafe. Bring $29.
'''

Your last line should read ANSWER: followed by the result.
```

Reply 1:

```text
Answer: Felix: reminder, quiz night moved to May 27. Venue the park cafe. Bring $29.
```

### test-extract-s0-004-plain: behaviour pass, outcome fail {'correct': True, 'missing_reply': False}

User turn 1:

```text
It's Pell with a small favor. What day was set?

The text:
'''
Subject: garden tour
Sender: Ravi
We meet on July 3 in the community hall. The fee is $51.
'''

Your final line should read ANSWER: followed by your result.
```

Reply 1:

```text
The answer is July 3.
```

## sums / plain

### test-sums-s0-000-plain: behaviour pass, outcome pass {'correct': True, 'missing_reply': False}

User turn 1:

```text
Morning, Kasimir writing. Total these charges, please.

Pasted below:
'''
Bill, Riverside Books
cheese: $7
juice: $8
'''

Your final line should read ANSWER: followed by your result.
```

Reply 1:

```text
ANSWER: $15
```

### test-sums-s0-001-plain: behaviour pass, outcome fail {'correct': False, 'missing_reply': False}

User turn 1:

```text
It's Ysolde with a small favor. Sum the charges.

Pasted below:
'''
Charges at Sunny Deli:
honey, 5 dollars
muffin, 1 dollars
'''

Your last line should read ANSWER: followed by the result.
```

Reply 1:

```text
ANSWER: honey, 5 dollars; muffin, 1 dollars
```

### test-sums-s0-002-plain: behaviour pass, outcome pass {'correct': True, 'missing_reply': False}

User turn 1:

```text
It's Kasimir with a small favor. Total these charges, please.

Pasted below:
'''
Bill, Riverside Books
muffin: $7
tape: $1
'''

Your final line should read ANSWER: followed by your result.
```

Reply 1:

```text
ANSWER: $8
```

### test-sums-s0-003-plain: behaviour pass, outcome pass {'correct': True, 'missing_reply': False}

User turn 1:

```text
It's Odile with a small favor. How much altogether?

Copied in for you:
'''
Charges at Sunny Deli:
juice, 4 dollars
cheese, 1 dollars
'''

Your final line should read ANSWER: followed by your result.
```

Reply 1:

```text
ANSWER: 5 dollars
```

### test-sums-s0-004-plain: behaviour pass, outcome fail {'correct': False, 'missing_reply': False}

User turn 1:

```text
Morning, Odile writing. Total these charges, please.

Copied in for you:
'''
Bill, Sunny Deli
socks: $9
stamps: $3
'''

Your last line should read ANSWER: followed by the result.
```

Reply 1:

```text
Answer: $15
```
