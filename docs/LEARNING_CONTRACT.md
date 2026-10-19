# Learning Contract

## Objective

Use AI to accelerate repetitive work while retaining independent understanding of the system.

## Before accepting generated code, I should be able to answer

1. What problem does this component solve?
2. What are its inputs, outputs and side effects?
3. Why was this approach chosen instead of a simpler alternative?
4. What happens with missing, duplicated, late or invalid data?
5. How do I test it with a known expected result?
6. What are its limitations?

## Red / amber / green ownership

- **Green — AI may draft:** boilerplate, formatting, README first drafts, simple test scaffolding, repetitive mappings.
- **Amber — AI drafts, I verify:** SQL transformations, DAX measures, API clients, model pipelines, data schemas.
- **Red — I must understand and decide:** business definitions, forecast validation design, source-of-truth decisions, interpretation of results, acceptance criteria, security and final claims in the portfolio.

## Weekly ritual

At the end of a week:
- Explain one feature aloud without reading the code.
- Reproduce one calculation manually.
- Make one small change without asking AI to do it.
- Record one misunderstanding or bug and what it taught you.
- Update the session log.

## If I cannot explain the code

Do not add more features. Ask for a smaller explanation, trace the data flow, build a tiny example, and test it. Rewrite the central logic in a simpler form if necessary.
