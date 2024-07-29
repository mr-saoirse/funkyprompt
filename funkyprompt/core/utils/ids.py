import json
import uuid
import hashlib


def uuid_str_from_dict(d):
    """
    generate a uuid string from a seed that is a sorted dict
    """
    d = json.dumps(d, sort_keys=True).encode("utf-8")
    m = hashlib.md5()
    m.update(d)
    return str(uuid.UUID(m.hexdigest()))


def funky_id(name: str = None):
    return uuid_str_from_dict({"name": name})


def funky_hash(s: str = None, length: int = 5, prefix="fun"):
    """
    generate a hash by some convention
    """
    if s:
        try:
            s = s.encode()
        except:
            pass
    s = s or str(uuid.uuid1()).encode()

    h = hashlib.shake_256(s).hexdigest(length).upper()

    return f"{prefix}{h}"
