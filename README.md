# Horizon Quiz Bot

Telegram bot that delivers the express-test result. The test page links
users here with a deep link like `https://t.me/<bot>?start=quiz_B2`
— the bot reads the level and replies with the level breakdown + the
Horizon offer.

## 1. Create the bot (2 min, in Telegram)

1. Open **@BotFather** → send `/newbot`.
2. Name: `Horizon Quiz` (or anything). Username: pick one, e.g. `horizon_quiz_bot`.
3. BotFather replies with an **API token** — copy it.

## 2. Deploy on Railway

1. New project → deploy from this folder (or the zip).
2. Add variables (Variables tab):
   - `BOT_TOKEN` = the token from BotFather
   - `PRICE` = `$49` (or `$55` — change anytime, no redeploy needed)
   - `PAYMENT_URL` = your Stripe payment link (when ready)
   - `TEST_URL` = `https://www.arghorizon.com/expresstest.html`
   - `COMMUNITY_URL` = invite link to the Horizon Telegram group
     (get it in the group: title → Add members → Invite to group via link).
     If left empty, the community button simply won't show.
3. Deploy. The bot starts polling automatically — no webhook setup needed.

## 3. Point the test page at the new bot

In `express-test-widget-v2.html`, change one line:

```js
const TG_BOT = "horrizzonn_bot";
```

to your new bot's username (without `@`):

```js
const TG_BOT = "horizon_quiz_bot";
```

Re-paste the widget into the Tilda T123 block and publish.

## How it works

- `/start quiz_A1` … `/start quiz_B2` → level message + offer with payment button
- `/start` (no payload) → welcome + "take the test" button
- anything else → nudge to press /start
