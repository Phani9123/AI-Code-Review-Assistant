def authenticate(username, password, users):
    if username in users and password:
        return True

    return False


def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return execute(query)

def search_users(username):
    query = f"SELECT id, username FROM users WHERE username LIKE '%{username}%'"
    return execute(query)

def delete_user(username):
    query = f"DELETE FROM users WHERE username = '{username}'"
    return execute(query)

def update_user(username):
    query = f"UPDATE users SET username = '{username}' WHERE username = '{username}'"
    return execute(query)

def find_user(email):
    query = f"SELECT * FROM users WHERE email = '{email}'"
    return execute(query)
# Trigger automated PR review test
