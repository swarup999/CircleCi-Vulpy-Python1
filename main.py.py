from flask import Flask, request, render_template_string, send_file
import sqlite3
import os

app = Flask(__name__)

# Initialize user database
def init_db():
    conn = sqlite3.connect('bookstore.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)')
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('sarah.smith', 'mypass123'))
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('john.doe', 'doe2023'))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return """
        <h1>Welcome to BookWorm Online Bookstore</h1>
        <p>Your one-stop shop for all your reading needs!</p>
        <a href="/login">Login</a> | <a href="/search">Search Books</a>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Vulnerable query
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        conn = sqlite3.connect('bookstore.db')
        cursor = conn.cursor()
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()

        if user:
            return f"""
                <h2>Welcome back, {user[1]}!</h2>
                <p>Browse our latest collection of books.</p>
                <a href="/search">Search Books</a>
            """
        else:
            return "Invalid email or password. Please try again."

    return '''
        <h2>Login to Your Account</h2>
        <form method="post">
            Email: <input type="text" name="username" placeholder="Enter your email"><br><br>
            Password: <input type="password" name="password" placeholder="Enter your password"><br><br>
            <input type="submit" value="Login" style="background-color: #4CAF50; color: white; padding: 10px 20px;">
        </form>
    '''

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')

    # Vulnerable template rendering
    html = f"""
        <h2>Book Search</h2>
        <form method="get">
            <input type="text" name="q" value="{query}" placeholder="Search for books...">
            <input type="submit" value="Search">
        </form>
        <h3>Search Results for: {query}</h3>
    """
    return render_template_string(html)

@app.route('/download', methods=['GET'])
def download():
    filename = request.args.get('file')

    # Vulnerable file access
    filepath = os.path.join('ebooks', filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    else:
        return "Sorry, the requested ebook is not available."

if __name__ == '__main__':
    app.run(debug=True)
