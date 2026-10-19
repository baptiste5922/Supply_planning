---
name: learning-first
description: Use for any implementation task where the developer wants to learn the concepts rather than blindly accept generated code.
---

# Learning-first implementation procedure

## Before coding

1. Restate the outcome in business language.
2. Identify what the user should learn from the task.
3. State inputs, outputs, assumptions and dependencies.
4. Propose the smallest useful implementation.
5. Name the files that will change and how success will be checked.

## During coding

- Work in small increments, preferably one function, query or workflow at a time.
- Explain unfamiliar syntax and concepts at the point of use.
- Prefer explicit code over clever one-liners.
- Ask the user to predict a result when that helps learning.
- Use small fixtures with hand-calculated expected outputs.
- Do not add a dependency without explaining its role.
- Keep reusable code out of notebooks.

## After coding

1. Run tests or provide an honest manual verification procedure.
2. Explain the most important design decisions and likely failure modes.
3. Ask the user to explain one core decision in their own words.
4. Give one optional modification exercise.
5. Summarise what changed and any known limitations.

## Do not

- Generate the entire project at once.
- equate passing tests with proof of correctness.
- hide assumptions inside code.
- claim that the user understands something just because code was generated.
