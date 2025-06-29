import secrets
import string


def generate_password(length=8):
    all_chars = string.ascii_letters + string.digits
    password = str()
    for _ in range(length):
        password += secrets.choice(all_chars)
    return password


print(generate_password())
