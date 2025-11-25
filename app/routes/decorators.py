def with_message(msg: str):
    def decorator(func):
        setattr(func, "response_message", msg)
        return func

    return decorator
