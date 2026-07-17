# Status Rules

Allowed statuses:

```text
OK
LOW_SCORE
MISSING_FIELDS
UNAVAILABLE
SELLER_MISMATCH
NOT_FOUND
PAGE_ERROR
ACCESS_BLOCKED
CAPTCHA
CONTINUE_SHOPPING
FETCH_FAILED
```

Rules:

- `OK`: page loads normally and score is at least 75 with no major business abnormality.
- `LOW_SCORE`: page loads normally but score is below 75.
- `MISSING_FIELDS`: page loads normally but key listing fields are missing.
- `UNAVAILABLE`: page says unavailable/out of stock or lacks buyability signals.
- `SELLER_MISMATCH`: configured seller ID/store does not match detected seller text.
- `NOT_FOUND`: ASIN page does not exist or Amazon returns a clear not-found page.
- `ACCESS_BLOCKED`: Amazon blocks access, robot-checks, or returns anti-automation content.
- `CAPTCHA`: captcha is visible.
- `CONTINUE_SHOPPING`: Amazon continue-shopping interstitial persists and reliable product facts are not available.
- `PAGE_ERROR`: page load or HTTP-level error.
- `FETCH_FAILED`: Chrome collection failed before reliable page state was captured.

`ACCESS_BLOCKED`, `CAPTCHA`, and unrecovered `CONTINUE_SHOPPING` are monitoring access states, not Listing quality states.

Recovery rule:

- If the collector labels a page `CONTINUE_SHOPPING` but still captures reliable product facts such as title, bullet points, image count, and category or BSR signals, the scorer should continue the Listing completeness review.
- In recovered cases, derive the final report status from Listing facts, such as `OK`, `LOW_SCORE`, `MISSING_FIELDS`, `UNAVAILABLE`, or `SELLER_MISMATCH`.
- Do not recover `CAPTCHA` or `ACCESS_BLOCKED`; those remain unreviewable.
