from flask import Flask, render_template, request, redirect, url_for, session, send_file
import os
import sqlite3
import ast
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DB_PATH = 'part2.sqlite'
QUESTION_TABLE = 'my_table'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            music_level INTEGER
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS question_responses (
            user_id TEXT,
            question_id TEXT,
            selected_option TEXT,
            difficulty_tag TEXT,
            comment TEXT,
            PRIMARY KEY (user_id, question_id)
        )
    ''')

    conn.commit()
    conn.close()

def get_question_ids():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM {QUESTION_TABLE}")
    ids = [row[0] for row in cur.fetchall()]
    conn.close()
    return ids

def get_question_by_id(qid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT id, question, final_options FROM {QUESTION_TABLE} WHERE id = ?", (qid,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0],
            'question': row[1],
            'options': ast.literal_eval(row[2])
        }
    return None

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/submit_user', methods=['POST'])
def submit_user():
    first_name = request.form['first_name'].strip().lower()
    last_name = request.form['last_name'].strip().lower()
    music_level = int(request.form['music_level'])

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE first_name = ? AND last_name = ? AND music_level = ?",
                (first_name, last_name, music_level))
    row = cur.fetchone()

    if row:
        user_id = row[0]
    else:
        user_id = str(uuid.uuid4())
        cur.execute("INSERT INTO users (user_id, first_name, last_name, music_level) VALUES (?, ?, ?, ?)",
                    (user_id, first_name, last_name, music_level))

    session['user_id'] = user_id
    conn.commit()

    question_ids = get_question_ids()
    cur.execute("SELECT question_id FROM question_responses WHERE user_id = ?", (user_id,))
    answered = {row[0] for row in cur.fetchall()}
    conn.close()

    next_qid = next((qid for qid in question_ids if qid not in answered), None)
    if next_qid:
        return redirect(url_for('form', qid=next_qid))
    else:
        return "Survey already completed. Thank you!"

@app.route('/form/<qid>', methods=['GET', 'POST'])
def form(qid):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('landing'))

    ids = get_question_ids()
    if qid not in ids:
        return "Question not found."

    current_index = ids.index(qid)

    if request.method == 'POST':
        selected_option = request.form.get('answer')
        difficulty_tag = request.form.get('difficulty_tag')
        comment = request.form.get('comment')

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO question_responses
            (user_id, question_id, selected_option, difficulty_tag, comment)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, qid, selected_option, difficulty_tag, comment))
        conn.commit()
        conn.close()

        if current_index < len(ids) - 1:
            return redirect(url_for('form', qid=ids[current_index + 1]))
        else:
            return "Survey completed. Thank you!"

    question = get_question_by_id(qid)

    # Fetch existing response
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT selected_option, difficulty_tag, comment
        FROM question_responses
        WHERE user_id = ? AND question_id = ?
    ''', (user_id, qid))
    row = cur.fetchone()
    conn.close()

    prev_selection = {
        'selected_option': row[0] if row else None,
        'difficulty_tag': row[1] if row else None,
        'comment': row[2] if row else ''
    }

    prev_id = ids[current_index - 1] if current_index > 0 else None
    next_id = ids[current_index + 1] if current_index < len(ids) - 1 else None

    return render_template('form.html',
                           question=question,
                           prev_id=prev_id,
                           next_id=next_id,
                           prev_selection=prev_selection)
@app.route('/download_db')
def download_db():
    if os.path.exists(DB_PATH):
        return send_file(DB_PATH, as_attachment=True)
    else:
        return "Database file not found.", 404
    
def setup():
    init_db()

if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=80)
