import hashlib
import random


def generate_key():
    return hashlib.sha1(str(random.random())).hexdigest()
