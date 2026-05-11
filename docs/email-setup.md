# Email Setup

---

## SendGrid (This is what I went with and what the .env is set-up with) - But u can use another service if u prefer

1. Sign up at [sendgrid.com](https://sendgrid.com) (free tier)
2. Go to **Settings → API Keys → Create API Key** (Full Access) → copy it
3. Go to **Settings → Sender Authentication → Single Sender Verification** → verify the address you want emails to come from
4. Add to your `.env`:

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your-api-key-here
SMTP_FROM=verified@youremail.com
```

## Dev / local (no real delivery)

Leave the defaults — emails are caught by MailHog and visible at `http://localhost:8025`. Nothing reaches a real inbox.

```env
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
```
