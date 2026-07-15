import requests
from main.funcs import send_message_bot, code_generator

def sender_code(phone):
    MERCHANT_ID = 212
    TOKEN = 'THpraofsxAqQnkjOPEFSdmeLvRKNluhtbBZXVyIUGiDJYMg'
    code = code_generator()
    TEXT = f"Tasdiqlash kodi: {code}"

    if phone.__len__() == 9:
        send_message_bot(TEXT+f"\nTelfon: {phone}")

        url = f"https://api.xssh.uz/smsv1/spes.php/?id={MERCHANT_ID}&token={TOKEN}&number={phone}&text={TEXT}"
        response = requests.request("GET", url)
        status = 'Xabar yuborildi'
    else:
        status = 'Xabar yuborilmadi'

    return {"status":status, "code":code}

def sender_gived_money(phone, text):
    MERCHANT_ID = 212
    TOKEN = 'THpraofsxAqQnkjOPEFSdmeLvRKNluhtbBZXVyIUGiDJYMg'
    TEXT = text

    if phone.__len__() == 9:
        url = f"https://api.xssh.uz/smsv1/spes.php/?id={MERCHANT_ID}&token={TOKEN}&number={phone}&text={TEXT}"
        response = requests.request("GET", url)

    return True