from flask import Flask, request, render_template, redirect
from werkzeug.utils import secure_filename

import os
import random
import datetime

from data import db_session
from data.boards import Boards
from data.posts import Posts

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'static/media/from_users'
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg', 'gif', 'webm', 'mp4', 'mp3', 'wav']


@app.route("/")
def index():
    db_sess = db_session.create_session()
    boards = db_sess.query(Boards)
    return render_template("index.html", boards=boards, boards_count=boards.count())


@app.route("/<board_name>", methods=['POST', 'GET'])
def board_url(board_name):
    if request.method == 'GET':
        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        for board_obj in board_select:
            posts = db_sess.query(Posts).filter(Posts.board_name == board_obj.name,
                                                Posts.parent_post == None)
            return render_template("board.html", board=board_obj, posts=posts, posts_count=posts.count())
        return render_template("error.html", code=404,
                               text="К сожалению, данная доска больше недоступна или её не существует.",
                               pics=["crab-rave.gif", "anon.png"])
    elif request.method == 'POST':
        post = Posts()
        t = datetime.datetime.now()
        post.time = t
        post.topic = request.form["topic"]
        post.text = request.form["text"]
        file = request.files["file"]
        print(file.filename)
        if file and allowed_file(file.filename):
            filename = str(t).replace(" ", "-").replace(".", "-").replace(":", "-").lower() + \
                       "." + file.filename.rsplit('.', 1)[1].lower()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.media = filename
            post.media_type = filename.rsplit('.', 1)[1].lower()
        post.board_name = board_name
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        return redirect(board_name)


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
                                       posts_count=posts.count())
        return render_template("error.html", code=404,
                               text="К сожалению, данный тред больше недоступен или его не существует.",
                               pics=["crab-rave.gif", "anon.png"])
    elif request.method == 'POST':
        post = Posts()
        t = datetime.datetime.now()
        post.time = t
        post.parent_post = post_id
        post.topic = request.form["topic"]
        post.text = request.form["text"]
        file = request.files["file"]
        print(file.filename)
        if file and allowed_file(file.filename):
            filename = str(t).replace(" ", "-").replace(".", "-").replace(":", "-").lower() + \
                       "." + file.filename.rsplit('.', 1)[1].lower()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.media = filename
            post.media_type = filename.rsplit('.', 1)[1].lower()
        post.board_name = board_name
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
