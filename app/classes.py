import importlib


def instantiate_class(full_class_path: str):
    try:
        module_path, class_name = full_class_path.rsplit(".", 1)
    except ValueError:
        raise ValueError(f"Invalid format for {full_class_path}")
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls()
