from flask import Flask, render_template, redirect, url_for, request, session, flash, g, jsonify
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv
from genailib_rg.genailib_rg_sub import get_chat_responses  # Ensure this is correctly imported
import hashlib
from functools import wraps

from sql import initialize_database  # Import the database initialization function

# Load environment variables from the .env file
load_dotenv()

DEVELOPMENT_ENV = True

# Initialize the database
initialize_database()

# Connect to database
def connect_db():
    return sqlite3.connect('sample.db')

app = Flask(__name__, template_folder='../templates')

# Config
app.secret_key = os.getenv("FLASK_SECRET_KEY")

app_data = {
    "name": "The learning chat",
    "description": "Making life easier since 2018!",
    "author": "SGG",
    "html_title": "SGG. Inc Invation that empowers",
    "project_name": "The Learing Chat",
    "keywords": "flask, webapp, tbasic",
}

# login required decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)

@app.route("/")
def index():
    return render_template("index.html", app_data=app_data)

@app.route("/about")
def about():
    return render_template("about.html", app_data=app_data)

@app.route("/chat", methods=['GET', 'POST'])
@login_required
def chat():
    g.db = connect_db()
    username = session['username']
    cur = g.db.execute('SELECT userid FROM users WHERE username = ?', (username,))
    user_id = cur.fetchone()[0]
    cur = g.db.execute('SELECT modelid FROM models WHERE modelname = ?', ('None',))
    model_id = cur.fetchone()[0]
    if request.method == 'POST':
        chat = request.form['chat']
        thetime = datetime.now()
        g.db.execute('INSERT INTO chats (user_id, model_id, chat, time) VALUES (?, ?, ?, ?)', (user_id, model_id, chat, thetime))
        g.db.commit()

    cur2 = g.db.execute('SELECT * FROM chats WHERE user_id = ? ORDER BY time;', (user_id,))
    chats = [dict(time=row[4], chat=row[3], chat_id=row[0]) for row in cur2.fetchall()]  # Add chat_id to the dictionary
    g.db.close()
    return render_template("chat.html", app_data=app_data, chats=chats)

@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.get_json()
    prompt = data.get('prompt', '')

    try:
        # Use get_chat_responses function directly
        chat_text = get_chat_responses(prompt, model="gpt-3.5-turbo")
        return jsonify({"response": chat_text})
    except Exception as e:
        return jsonify({"error": str(e)})


def lookup_user(username, password):
    g.db = connect_db()
    cur = g.db.execute('SELECT userid, username, password FROM users WHERE username = ?', (username,))
    user_id, lookedup_username, lookedup_password = cur.fetchone()
    g.db.close()
    if not verify_password(lookedup_password, password):
        raise ValueError("Password does not match")
    return lookedup_username

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        try:
            username = lookup_user(request.form['username'], request.form['password'])
            session['logged_in'] = True
            session['username'] = username
            flash('You were logged in.')
            return redirect(url_for('index'))
        except ValueError as e:
            error = f"Invalid Credentials. {str(e)} Please try again."
    return render_template('login.html', app_data=app_data, error=error)

@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You were logged out.')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    g.db = connect_db()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        g.db.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)',  (username, hashed_password,))
        g.db.commit()
        session['logged_in'] = True
        session['username'] = request.form['username']
        flash('You were logged in.')
        return redirect(url_for('index'))
    return render_template('register.html', app_data=app_data)

if __name__ == "__main__":
    app.run(debug=DEVELOPMENT_ENV)

#Log in details
#1. admin, admin
#2. example, example
#3. Regina, Regina