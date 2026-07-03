import hashlib


def phone_hash(phone_number: str, pepper: str) -> str:
    return hashlib.sha256(f"{pepper}:{phone_number}".encode()).hexdigest()


def mask_phone(phone_number: str) -> str:
    if len(phone_number) <= 4:
        return "*" * len(phone_number)
    return f"{phone_number[:1]}{'*' * (len(phone_number) - 5)}{phone_number[-4:]}"
