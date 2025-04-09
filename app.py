from flask import Flask, render_template, request, session, redirect, url_for
import json
import random
import os
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key'

with open('pitches.json') as f:
    pitch_data = json.load(f)

LEADERBOARD_FILE = 'leaderboard.json'

@app.route('/')
def start():
    session.clear()
    return render_template('start.html')

@app.route('/pitch')
def pitch():
    mode = request.args.get("mode") or session.get("mode", "leaderboard")
    session["mode"] = mode

    if mode == "game" and "inning" not in session:
        session.update({
            "inning": 1,
            "outs": 0,
            "balls": 0,
            "strikes": 0,
            "runs": 0,
            "runners": [False, False, False],
            "hits": 0,
            "outs_total": 0,
            "at_bats": 0
        })

    if mode == "leaderboard" and session.get("total", 0) >= 10 and session.get("streak", 0) < 3:
        return redirect(url_for('summary'))

    selected_pitch = random.choice(pitch_data)
    session["selected_pitch"] = selected_pitch
    session["start_time"] = time.time()

    return render_template(
        "pitch.html",
        pitch=selected_pitch,
        score=session.get("score", 0),
        total=session.get("total", 0),
        streak=session.get("streak", 0),
        mode=mode
    )

@app.route('/result', methods=['POST'])
def result():
    user_guess = request.form['pitch_guess']
    user_decision = request.form['swing_take']
    correct_pitch = request.form['correct_pitch']
    correct_zone = request.form['ball_or_strike']
    mode = session.get("mode", "leaderboard")

    reaction_time = round(time.time() - session.get("start_time", time.time()), 3)
    correct_guess = user_guess == correct_pitch
    correct_swing = (
        (user_decision == "Swing" and correct_zone == "Strike") or
        (user_decision == "Take" and correct_zone == "Ball")
    )
    is_correct = correct_guess and correct_swing

    session["score"] = session.get("score", 0)
    session["total"] = session.get("total", 0)
    session["streak"] = session.get("streak", 0)
    session["total"] += 1

    hit_type = None
    if mode == "game":
        inning = session.get("inning", 1)
        outs = session.get("outs", 0)
        balls = session.get("balls", 0)
        strikes = session.get("strikes", 0)
        runners = session.get("runners", [False, False, False])
        runs = session.get("runs", 0)
        hits = session.get("hits", 0)
        outs_total = session.get("outs_total", 0)
        at_bats = session.get("at_bats", 0)

        at_bats += 1

        if user_decision == "Take":
            if correct_zone == "Ball":
                balls += 1
                if balls >= 4:
                    runners, runs = advance_runners(runners, 1, runs)
                    balls = 0
                    strikes = 0
            else:
                strikes += 1

        elif user_decision == "Swing":
            if correct_zone == "Strike":
                if correct_guess:
                    if reaction_time <= 0.5:
                        hit_type = "Home Run"
                        runners, runs = advance_runners(runners, 4, runs)
                        hits += 1
                    elif reaction_time <= 1.0:
                        hit_type = "Triple"
                        runners, runs = advance_runners(runners, 3, runs)
                        hits += 1
                    elif reaction_time <= 1.5:
                        hit_type = "Double"
                        runners, runs = advance_runners(runners, 2, runs)
                        hits += 1
                    elif reaction_time <= 2.0:
                        hit_type = "Single"
                        runners, runs = advance_runners(runners, 1, runs)
                        hits += 1
                    else:
                        strikes += 1
                else:
                    if strikes < 1:
                        strikes += 1
            else:
                strikes += 1

        if strikes >= 2:
            outs += 1
            outs_total += 1
            balls = 0
            strikes = 0

        if outs >= 2:
            inning += 1
            outs = 0
            balls = 0
            strikes = 0
            runners = [False, False, False]

        if inning > 7:
            session.update({
                "hits": hits,
                "outs_total": outs_total,
                "at_bats": at_bats
            })
            return redirect(url_for('game_summary'))

        session.update({
            "inning": inning,
            "outs": outs,
            "balls": balls,
            "strikes": strikes,
            "runs": runs,
            "runners": runners,
            "hits": hits,
            "outs_total": outs_total,
            "at_bats": at_bats
        })

    if mode != "game":
        if is_correct:
            session["score"] += 1
            session["streak"] += 1
        else:
            session["streak"] = 0

    session.pop("selected_pitch", None)
    session.pop("start_time", None)

    return render_template(
        "result.html",
        correct_pitch=correct_pitch,
        user_guess=user_guess,
        correct_zone=correct_zone,
        user_decision=user_decision,
        thumbs_up=is_correct,
        score=session["score"],
        total=session["total"],
        streak=session["streak"],
        mode=mode,
        reaction_time=reaction_time,
        hit_type=hit_type,
        inning=session.get("inning"),
        outs=session.get("outs"),
        balls=session.get("balls"),
        strikes=session.get("strikes"),
        runs=session.get("runs"),
        runners=session.get("runners")
    )

def advance_runners(runners, bases, runs):
    new_runners = [False, False, False]
    scoring = 0
    if bases == 4:
        scoring += sum(runners) + 1
    else:
        for i in reversed(range(3)):
            if runners[i]:
                if i + bases >= 3:
                    scoring += 1
                else:
                    new_runners[i + bases] = True
        if bases < 4:
            new_runners[bases - 1] = True
    return new_runners, runs + scoring

@app.route('/summary')
def summary():
    score = session.get('score', 0)
    total = session.get('total', 1)
    avg = round(score / total, 3)
    avg_str = "{:.3f}".format(avg)[1:]
    return render_template(
        'summary.html',
        score=score,
        total=total,
        avg=avg,
        avg_str=avg_str,
        mode=session.get("mode", "leaderboard"),
        runs=session.get("runs", 0)
    )

@app.route('/game_summary')
def game_summary():
    runs = session.get("runs", 0)
    outs = session.get("outs_total", 0)
    hits = session.get("hits", 0)
    total_at_bats = session.get("at_bats", 1)
    avg = "{:.3f}".format(hits / total_at_bats)[1:]
    return render_template("final_scoreboard.html", runs=runs, outs_total=outs, hits=hits, avg=avg)

@app.route('/submit_score', methods=['POST'])
def submit_score():
    name = request.form['name']
    score = session.get('score', 0)
    total = session.get('total', 1)
    avg = round(score / total, 3)

    entry = {"name": name, "score": score, "total": total, "avg": avg}

    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r') as f:
            leaderboard = json.load(f)
    else:
        leaderboard = []

    leaderboard.append(entry)
    leaderboard.sort(key=lambda x: x['avg'], reverse=True)

    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(leaderboard, f, indent=4)

    return redirect(url_for('leaderboard'))

@app.route('/leaderboard')
def leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r') as f:
            raw_board = json.load(f)
    else:
        raw_board = []

    for entry in raw_board:
        entry['avg_str'] = "{:.3f}".format(entry['avg'])[1:]

    return render_template('leaderboard.html', leaderboard=raw_board)

if __name__ == '__main__':
    app.run(debug=True)
