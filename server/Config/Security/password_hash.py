import bcrypt

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using a randomly generated salt.
    The resulting hash contains the salt within it.
    """
    # 1. Convert string to bytes
    pwd_bytes = password.encode('utf-8')
    # 2. Generate a salt (default cost is 12 rounds in 2025)
    salt = bcrypt.gensalt()
    # 3. Hash the password
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    # 4. Return as string for storage in Postgres
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against the stored hash.
    """
    # 1. Convert both to bytes for comparison
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    # 2. Check and return boolean
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)
