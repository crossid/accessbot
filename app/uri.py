from urllib.parse import parse_qs, urlparse


class ParsedURI:
    scheme: str

    def __init__(self, uri: str, params_no_array=True):
        parsed = urlparse(uri)
        qp = parse_qs(parsed.query)
        if params_no_array:
            qp = {k: v[0] if len(v) == 1 else v for k, v in qp.items()}
        self.scheme = parsed.scheme
        self.netloc = parsed.netloc
        self.parameters = qp
