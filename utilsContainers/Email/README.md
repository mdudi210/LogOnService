# Email Container (Mailpit)

This utility container provides a local SMTP inbox for testing LogOnService email delivery.

## Start

```bash
cd utilsContainers/Email
docker compose up -d
```

## Access

- SMTP: `localhost:${MAILPIT_SMTP_PORT:-1025}`
- Web UI: `http://localhost:${MAILPIT_UI_PORT:-8025}`

## Stop

```bash
docker compose down
```

## Notes

- Mailpit accepts any recipient address.
- No real emails are sent externally.
- In the main app Docker setup, the backend points SMTP to the `email` service automatically.
