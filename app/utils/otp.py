import secrets


def generate_numeric_otp(length: int = 6) -> str:
    if length <= 0:
        raise ValueError("length must be positive")
    return "".join(str(secrets.randbelow(10)) for _ in range(length))
