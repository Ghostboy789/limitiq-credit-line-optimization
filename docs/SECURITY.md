# Application security controls

LimitIQ is an educational demonstration and must not receive real customer,
account, bureau, income or lending data. The controls below reduce risk for the
public demo; they do not make it a production lending service.

## Input and resource bounds

- Every POST request envelope is capped before framework parsing at
  `MAX_UPLOAD_BYTES + 64 KiB`. The default is a 5 MiB payload allowance plus
  64 KiB of multipart overhead.
- Batch CSV files are separately limited to 5 MiB and 5,000 rows.
- `/batch`, `/simulator` POST, `/api/predict` and `/v4-lab/reviews`
  share a per-client-IP token bucket: a burst of 60 requests and a refill of one
  token per second. At most 10,000 client keys are retained.
- The client address comes from the ASGI server's connection scope. A trusted
  deployment proxy must normalize it; the application does not trust a raw
  forwarded-address header.

The token bucket is process-local, best-effort protection. It resets on restart
and is not coordinated between workers or hosts. A production-scale service
would enforce distributed limits at a trusted reverse proxy or gateway.

## Review demonstration

The maker-checker ledger retains at most 500 events with FIFO eviction, and the
lab page renders only the latest 100. It is anonymous, process-local synthetic
demo state—not durable audit storage.

Review forms use a per-client double-submit CSRF token. The token cookie is
`HttpOnly`, `SameSite=Strict`, restricted to the `/v4-lab` path and marked
`Secure` under HTTPS. Token-bearing pages are sent with `Cache-Control:
no-store`.

## Output and container controls

CSV exports prefix cells beginning with `=`, `+`, `-`, `@`, tab or
carriage return with an apostrophe to prevent spreadsheet formula execution.

The container runs as a non-root application user and includes only the four
model files loaded by the web runtime: the behavioral candidate, its metadata
and feature schema, and the global research metadata. CI builds the image,
starts it and requires `/health` to succeed before the benchmark step.
