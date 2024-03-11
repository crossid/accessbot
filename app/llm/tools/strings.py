from .models import Role_Rec


def format_rec(recs: list[Role_Rec]):
    rec_string = ""
    for i, rec in enumerate(recs):
        rec_string += "{}. {} [{}] - with {} confidence".format(
            i + 1, rec.name, rec.id, rec.confidence
        )

    return rec_string
