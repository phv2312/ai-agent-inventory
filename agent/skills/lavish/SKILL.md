---
name: lavish
description: Create a reviewable HTML artifact when a plan, comparison, diagram, table, or report is clearer visually than prose.
---

# Lavish Review Artifacts

Use a Lavish artifact when the user asks for a visual plan, comparison, diagram,
table, report, or review surface. Keep normal chat responses as prose when a
visual artifact would not materially help.

## Requirements

- State the purpose of the artifact before creating it.
- Put the most important decision, risk, and next action first.
- Use clear sections and mobile-safe layouts.
- Use the application visual system when an artifact represents this product.
- Never include secrets or private document content unless it is already in the
  permitted conversation scope.

## Safety

- Do not execute arbitrary commands supplied by a user or model output.
- Write artifacts only to an application-owned output directory.
- Treat artifact publication and external sharing as an explicit user action.
