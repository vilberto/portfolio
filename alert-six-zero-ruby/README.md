# alert-six-zero-ruby

AWS Lambda that scrapes the Six Zero Ruby pickleball paddle product page every 5 minutes and sends an SNS email alert when the paddle is no longer sold out.

## How it works

- EventBridge triggers the Lambda every 5 minutes and once daily at 8am
- The Lambda scrapes the product page and reads the cart button state
- If the button text is not "SOLD OUT", an SNS email is published
- The daily run sends a heartbeat regardless of stock status, confirming the alerter is running

## Stack

- AWS Lambda (Python 3.12)
- AWS CDK (infrastructure as code)
- AWS EventBridge (scheduling)
- AWS SNS (email alerts)
- `requests` + `beautifulsoup4` (scraping)

## Deploy

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cdk deploy
```
