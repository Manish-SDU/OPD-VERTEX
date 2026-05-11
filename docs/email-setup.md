# Email Setup

The app sends emails via SMTP. Two options:

---

## Option A — SendGrid (recommended, 100 free emails/day)

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

---

## Option B — Gmail

1. Enable 2-Step Verification on your Google account
2. Go to **Security → App passwords** → create one → copy the 16-character password
3. Add to your `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=you@gmail.com
```

---

## Dev / local (no real delivery)

Leave the defaults — emails are caught by MailHog and visible at `http://localhost:8025`. Nothing reaches a real inbox.

```env
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
```
