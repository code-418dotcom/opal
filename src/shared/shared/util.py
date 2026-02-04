import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def new_correlation_id() -> str:
    return uuid.uuid4().hex
