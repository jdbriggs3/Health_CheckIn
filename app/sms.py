"""
Sending a text message — behind a single simple function: send_sms().

Right now it just PRINTS the message to your terminal (the "fake" backend), so
you can build and test the whole conversation with no Twilio account, no cost,
and no phones involved. Later, wiring in real Twilio means changing ONLY this
file — nothing else in the app has to know the difference.
"""


def send_sms(to: str, body: str) -> None:
    """Pretend to send a text. For now, show it in the terminal."""
    print(f"\n\U0001F4E4  SMS to {to}:\n    {body}\n")


# When you're ready for real texts, you'll add a Twilio version roughly like:
#
#   from twilio.rest import Client
#   client = Client(ACCOUNT_SID, AUTH_TOKEN)
#   def send_sms(to, body):
#       client.messages.create(to=to, from_=TWILIO_NUMBER, body=body)
#
# ...and everything else keeps working unchanged.