
import sqlite3
from passlib.hash import pbkdf2_sha256

def db_init():

    users = [
        ('admin', pbkdf2_sha256.encrypt('123456789')),
        ('john', pbkdf2_sha256.encrypt('Password')),
        ('tim', pbkdf2_sha256.encrypt('Vaider2'))
    ]

    conn = sqlite3.connect('users.sqlite')
    c = conn.cursor()
    c.execute("DROP TABLE users")
    c.execute("CREATE TABLE users (user text, password text, failures int)")

    for u,p in users:
        c.execute("INSERT INTO users (user, password, failures) VALUES ('%s', '%s', '%d')" %(u, p, 1))

    conn.commit()
    conn.close()


@staticmethod
async def domain():
    domain = input("Test Domain: ")
    output = subprocess.check_output(f"nslookup {domain}", shell=True, encoding='UTF-8')
    print(output)

def find_user(username):
    with connection.cursor() as cur:
        cur.execute(f"""select username from USERS where name = '%s'""" % username)
        output = cur.fetchone()
    return output

if __name__ == '__main__':
    db_init()
