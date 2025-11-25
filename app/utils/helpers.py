import random
import string
from enum import Enum

import sqlalchemy as sa


def generate_random_string(length: int) -> str:
    """
    Generate random alphanumeric string based on specified length

    Args:
        length (int): The length of the string

    Returns:
        str: The random string
    """
    letters_and_digits = string.ascii_lowercase + string.digits
    rand_string = "".join(random.choice(letters_and_digits) for i in range(length))
    return rand_string


def generate_reference(prefix: str, length: int = 8):
    return f"{prefix}{generate_random_string(length)}"


def create_migration_enum_def(enumType: Enum, name: str):
    """
    Create a SQLAlchemy Enum definition for use in database migrations.

    Args:
        enumType (Enum): The Python Enum class to convert to a database enum
        name (str): The name to give the enum type in the database

    Returns:
        sa.Enum: A SQLAlchemy Enum definition ready for use in migrations
    """
    return sa.Enum(*[e.value for e in enumType], name=name)


def generate_random_token(length=4):
    token = "".join([str(random.randint(0, 9)) for _ in range(length)])
    return token
