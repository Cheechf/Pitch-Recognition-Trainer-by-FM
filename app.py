from flask import Flask, render_template, request, session, redirect, url_for
import json
import random
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'

with open('pitches.json') as f:
    pitch_data = json.load(f)

LEADERBOARD_FILE = 'leaderboard.json'

@app.route('/')
def start():
    session.clear()
    session['score'] = 0
    session['total'] = 0
    session['streak'] = 0
    return render_template('start.html')

@app.route('/pitch')
def pitch():
    # End session after 10 pitches unless streak is still 3+
    if session.get('total', 0) >= 10 and session.get('streak', 0) < 3:
        return redirect(url_for('summary'))

    if 'selected_pitch' not in session:
        session['selected_pitch'] = random.choice(pitch_data)

    return render_template(
        'pitch.html',
        pitch=session['selected_pitch'],
        score=session.get('score', 0),
        total=session.get('total', 0),
        streak=session.get('streak', 0)
    )

@app.route('/result', methods=['POST'])
def result():
    user_guess = request.form['pitch_guess']
    user_decision = request.form['swing_take']
    correct_pitch = request.form['correct_pitch']
    correct_zone = request.form['ball_or_strike']

    correct_guess = user_guess == correct_pitch
    correct_swing = (
        (user_decision == "Swing" and correct_zone == "Strike") or
        (user_decision == "Take" and correct_zone == "Ball")
    )
    is_correct = correct_guess and correct_swing

    session['score'] = session.get('score', 0)
    session['total'] = session.get('total', 0)
    session['streak'] = session.get('streak', 0)

    session['total'] += 1

    if is_correct:
        session['score'] += 1
        session['streak'] += 1
    else:
        session['streak'] = 0

    session.pop('selected_pitch', None)

    return render_template(
        'result.html',
        correct_pitch=correct_pitch,
        user_guess=user_guess,
        correct_zone=correct_zone,
        user_decision=user_decision,
        thumbs_up=is_correct,
        score=session['score'],
        total=session['total'],
        streak=session['streak']
    )

@app.route('/summary')
def summary():
    score = session.get('score', 0)
    total = session.get('total', 1)
    avg = round(score / total, 3)
    avg_str = "{:.3f}".format(avg)[1:]  # .300 format
    return render_template('summary.html', score=score, total=total, avg=avg, avg_str=avg_str)

@app.route('/submit_score', methods=['POST'])
def submit_score():
    name = request.form['name']
    score = session.get('score', 0)
    total = session.get('total', 1)
    avg = round(score / total, 3)

    entry = {"name": name, "score": score, "total": total, "avg": avg}

    if os.path.exists('leaderboard.json'):
        with open('leaderboard.json', 'r') as f:
            leaderboard = json.load(f)
    else:
        leaderboard = []

    leaderboard.append(entry)
    leaderboard.sort(key=lambda x: x['avg'], reverse=True)

    with open('leaderboard.json', 'w') as f:
        json.dump(leaderboard, f, indent=4)

    return redirect(url_for('leaderboard'))

@app.route('/leaderboard')
def leaderboard():
    if os.path.exists('leaderboard.json'):
        with open('leaderboard.json', 'r') as f:
            raw_board = json.load(f)
    else:
        raw_board = []

    for entry in raw_board:
        entry['avg_str'] = "{:.3f}".format(entry['avg'])[1:]  # .300 style

    return render_template('leaderboard.html', leaderboard=raw_board)

if __name__ == '__main__':
    app.run(debug=True)