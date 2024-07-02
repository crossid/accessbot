def add_prefix(string, prefix):
    if not string.startswith(prefix):
        string = prefix + string
    return string
