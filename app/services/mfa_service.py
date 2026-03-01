from app.utils.otp import generate_numeric_otp


def create_mfa_challenge_code() -> str:
    return generate_numeric_otp(6)
