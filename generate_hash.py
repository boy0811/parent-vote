from werkzeug.security import generate_password_hash

new_password = "1234"
hashed_password = generate_password_hash(new_password)
print(hashed_password)
