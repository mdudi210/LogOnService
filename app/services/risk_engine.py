def assess_login_risk(ip_address: str, is_new_device: bool) -> str:
    if is_new_device:
        return "high"
    if ip_address.startswith("10.") or ip_address.startswith("192.168."):
        return "low"
    return "medium"
