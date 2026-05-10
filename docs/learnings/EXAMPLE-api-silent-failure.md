---
date: 2026-03-01
category: api-gotcha
applies_to: any API integration
---

# API Returning 200 OK Does Not Mean It Worked

## What Happened

An email template was submitted to an API. The API accepted the request (200 OK), the workflow went live, events triggered, but the email never sent. No error was ever returned. 3+ hours were spent debugging event flow, subscriptions, and triggers before discovering the API had silently accepted invalid template syntax.

## The Learning

API success responses (200, 201, 202) do not guarantee the operation worked as intended. Some APIs accept invalid input silently and fail at execution time with no feedback.

## How to Apply

After any API call that creates or updates a resource:
1. Read the resource back (GET) to verify it was stored correctly
2. If the resource has a preview/render mode, check it
3. Don't trust status codes alone — verify the OUTCOME, not the acknowledgment
