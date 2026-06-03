import requests
from bs4 import BeautifulSoup


class Alerter:
    def __init__(self):

        self.trigger_alert = False
        self.url = "https://www.sixzeropickleball.com/collections/paddles/products/ruby"

        page = requests.get(self.url)
        soup = BeautifulSoup(page.content, "html.parser")

        # Get "Add to cart" button element
        element = soup.find("div", class_="payment-buttons").span

        self.default_text = element["data-default-text"].strip().upper()
        self.button_text = element.get_text(strip=True).upper()

        self.subject = f"SIX ZERO RUBY - {self.button_text}"
        self.message = (
            f"button_text: {self.button_text}; default_text: {self.default_text}"
        )

        # Trigger when button says "ADD TO CART" or not "SOLD OUT"
        if self.button_text == self.default_text or self.button_text != "SOLD OUT":
            self.trigger_alert = True
