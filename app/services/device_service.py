def is_known_device(device_fingerprint: str, known_fingerprints: set[str]) -> bool:
    return device_fingerprint in known_fingerprints
