---
description: Seed realistic dummy expenses for a specific user
argument-hint: "<user_id> <count> <months>"
allowed-tools: Read, Bash(python3:*)
---

Read database/db.py to understand the expenses table
schema, the db connection pattern, and the database
file name.

User input: $ARGUMENTS

## Step 1 — Parse arguments

Extract from $ARGUMENTS:
- user_id — integer
- count — integer, number of expenses to create
- months — integer, how many past months to spread them across

If any argument is missing or not a valid integer, stop and say:
"Usage: /seed-expenses <user_id> <count> <months>
Example: /seed-expenses 1 50 6"

## Step 2 — Validate the user

Query the users table (parameterised) for <user_id>. If no
such user exists, stop and say:
"No user with id <user_id> found. Run /seed-user first."

## Step 3 — Generate and insert

Write and run a Python script using Bash that:

1. Spreads expenses randomly across the past <months> months
   (dates never in the future, stored as YYYY-MM-DD)
2. Uses these categories with realistic Pakistani descriptions
   (e.g. rickshaw fare, K-Electric bill, chai and paratha,
   Servis shoes) and amounts in PKR:
   - Food: 50–800
   - Transport: 20–500
   - Bills: 200–3000
   - Health: 100–2000
   - Entertainment: 100–1500
   - Shopping: 200–5000
   - Other: 50–1000
3. Distributes categories roughly proportionally
   (Food most common, Health and Entertainment least)
4. Uses the db connection pattern from db.py — do not
   hardcode the database filename
5. Uses parameterised queries only — no string formatting in SQL
6. Inserts all expenses in a single transaction —
   roll back everything if any insert fails

## Step 4 — Confirm

Print:
- How many expenses were inserted
- The date range they span
- A sample of 5 inserted records