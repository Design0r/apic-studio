def sanitize_string(value: str) -> str:
    return "".join(c for c in value if c.isalnum() or c in (" ", "_", "-")).strip()
