from flask import Flask, request, render_template, redirect

import os

from data import db_session
from data.boards import Boards
from data.posts import Posts

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'static/media/from_users'
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024

image_files = ["png", "jpg", "jpeg", "gif", "jfif", "pjpeg", "pjp", "jpe", "webp"]
video_files = ["webm", "mp4", "m4v"]
audio_files = ["mp3", "wav"]

allowed_files = image_files + video_files + audio_files


def make_accept_for_html(mime):
    if mime in image_files:
        return "image/" + mime
    elif mime in video_files:
        return "video/" + mime
    elif mime in audio_files:
        return "audio/" + mime


accept = ",".join([make_accept_for_html(x) for x in allowed_files])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_files


@app.route("/")
def index():
    db_sess = db_session.create_session()
    boards = db_sess.query(Boards)
    posts = {}
    for board in boards:
        posts[board.name] = db_sess.query(Posts).filter(Posts.board_name == board.name).count()
    return render_template("index.html", boards=boards, boards_count=boards.count(), posts=posts)


@app.route("/robots.txt")
def robots():
    return f"<pre>{open('robots.txt', 'r').read()}</pre>"


@app.route("/<board_name>", methods=['POST', 'GET'])
def board_url(board_name):
    if request.method == 'GET':
        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        for board_obj in board_select:
            posts = db_sess.query(Posts).filter(Posts.board_name == board_obj.name,
                                                Posts.parent_post == None)
            post_answers = {}
            for post in posts:
                post_answers[post.id] = db_sess.query(Posts).filter(Posts.parent_post == post.id).count()
            return render_template("board.html", board=board_obj, posts=posts, posts_count=posts.count(),
                                   post_answers=post_answers, image_files=image_files, video_files=video_files,
                                   sound_files=audio_files, accept_files=accept)
        return render_template("error.html", code=404,
                               text="К сожалению, данная доска больше недоступна или её не существует.",
                               pics=["crab-rave.gif", "anon.png"])
    elif request.method == 'POST':
        ip = request.remote_user
        # ip = request.headers['X-Real-IP']
        # FOR PYTHONANYWHERE.COM
        if "like" in request.form:
            db_sess = db_session.create_session()
            post = db_sess.query(Posts).filter(Posts.id == request.form["like"])
            for p in post:
                if ip not in p.raters:
                    p.likes += 1
                    if p.raters:
                        raters = p.raters.split(";")
                        raters.append(ip)
                        p.raters = ";".join(raters)
                    else:
                        p.raters = ip
            db_sess.commit()
            return redirect(board_name)
        elif "dislike" in request.form:
            db_sess = db_session.create_session()
            post = db_sess.query(Posts).filter(Posts.id == request.form["dislike"])
            for p in post:
                if ip not in p.raters:
                    p.dislikes += 1
                    if p.raters:
                        raters = p.raters.split(";")
                        raters.append(ip)
                        p.raters = ";".join(raters)
                    else:
                        p.raters = ip
            db_sess.commit()
            return redirect(board_name)
        if not (request.form["topic"] or request.form["text"] or request.files["file"]):
            return redirect(board_name)
        post = Posts()
        post.topic = request.form["topic"]
        post.text = request.form["text"]
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = str(post.time).replace(" ", "-").replace(".", "-").replace(":", "-").lower() + \
                       "." + file.filename.rsplit('.', 1)[1].lower()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.media = filename
            post.media_type = filename.rsplit('.', 1)[1].lower()
            post.media_name = file.filename
        post.board_name = board_name
        post.poster = ip
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        return redirect(board_name + "/" + str(post.id))


@app.route("/<board_name>/<post_id>", methods=['POST', 'GET'])
def post_url(board_name, post_id):
    if request.method == 'GET':
        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        post_select = db_sess.query(Posts).filter(Posts.id == post_id,
                                                  Posts.board_name == board_name,
                                                  Posts.parent_post == None)
        for board_obj in board_select:
            for post_obj in post_select:
                posts = db_sess.query(Posts).filter(Posts.parent_post == post_id)
                return render_template("post.html", board=board_obj, the_post=post_obj, posts=posts,
                                       posts_count=posts.count(), image_files=image_files, video_files=video_files,
                                       sound_files=audio_files, accept_files=accept)
        return render_template("error.html", code=404,
                               text="К сожалению, данный тред больше недоступен или его не существует.",
                               pics=["crab-rave.gif", "anon.png"])
    elif request.method == 'POST':
        ip = request.remote_user
        # ip = request.headers['X-Real-IP']
        # FOR PYTHONANYWHERE.COM
        if "like" in request.form:
            db_sess = db_session.create_session()
            post = db_sess.query(Posts).filter(Posts.id == request.form["like"])
            for p in post:
                if ip not in p.raters:
                    p.likes += 1
                    if p.raters:
                        raters = p.raters.split(";")
                        raters.append(ip)
                        p.raters = ";".join(raters)
                    else:
                        p.raters = ip
            db_sess.commit()
            return redirect(post_id)
        elif "dislike" in request.form:
            db_sess = db_session.create_session()
            post = db_sess.query(Posts).filter(Posts.id == request.form["dislike"])
            for p in post:
                if ip not in p.raters:
                    p.dislikes += 1
                    if p.raters:
                        raters = p.raters.split(";")
                        raters.append(ip)
                        p.raters = ";".join(raters)
                    else:
                        p.raters = ip
            db_sess.commit()
            return redirect(post_id)
        if not (request.form["topic"] or request.form["text"] or request.files["file"]):
            return redirect(post_id)
        post = Posts()
        post.parent_post = post_id
        post.topic = request.form["topic"]
        post.text = request.form["text"]
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = str(post.time).replace(" ", "-").replace(".", "-").replace(":", "-").lower() + \
                       "." + file.filename.rsplit('.', 1)[1].lower()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.media = filename
            post.media_type = filename.rsplit('.', 1)[1].lower()
            post.media_name = file.filename
        post.board_name = board_name
        post.poster = ip
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        return redirect(post_id)


@app.errorhandler(404)
def error404(e):
    print(e)
    return render_template("error.html", code=404,
                           text="К сожалению, данный материал больше недоступен или его не существует.",
                           pics=["crab-rave.gif", "anon.png"])


@app.errorhandler(413)
def error413(e):
    print(e)
    return render_template("error.html", code=413,
                           text="Извините, но прикреплённый файл оказался по размерам слишком крут "
                                "и опасен для сервера, поэтому сервер подписал отказ в отправке.",
                           pics=["too_cool_and_dangerous.gif"])


@app.errorhandler(500)
def error500(e):
    print(e)
    return render_template("error.html", code=500,
                           text="По причинческим технинам сервер подписал отказ. "
                                "Извините за доставленные неудобства.",
                           pics=["prichincheskaya_tehnina.png"])


def main():
    db_session.global_init("db/imageboard.db")
    app.run(host="0.0.0.0")


if __name__ == '__main__':
    main()
