from nanoid import generate as _generate
from nanoid.resources import alphabet

SIZE = 10


def is_valid_nanoid(id_str):
    if len(id_str) != SIZE:
        return False
    return all(char in alphabet for char in id_str)


def generate():
    return _generate(alphabet=alphabet, size=SIZE)
