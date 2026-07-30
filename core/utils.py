from core.settings import AFRICASTALKING_API_KEY, AFRICASTALKING_USERNAME
import africastalking

africastalking.initialize(AFRICASTALKING_USERNAME, AFRICASTALKING_API_KEY)
sms = africastalking.SMS



def send_sms(phone_number, message):
    """
    Send an SMS message to a phone number.
    """
    try:
        response = sms.send(message, [phone_number])
        return response
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return None