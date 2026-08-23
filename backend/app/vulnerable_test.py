def authenticate(username, password, users):
    if username in users and password:
        return True

    return False


def test_change():
    return True