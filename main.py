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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ['png', 'jpg', 'jpeg', 'gif', 'webm', 'mp4', 'mp3', 'wav']


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
        return render_template("404.html")
    elif request.method == 'POST':
        post = Posts()
        post.time = datetime.datetime.now()
        post.topic = request.form["topic"]
        post.text = request.form["text"]
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = "".join([random.choice([
                                "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"
                                ]) for _ in range(16)]) + secure_filename(file.filename)
            print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.media = filename
            post.media_type = filename.rsplit('.', 1)[1]
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
        post_select = db_sess.query(Posts).filter(Posts.id == post_id)
        for board_obj in board_select:
            for post_obj in post_select:
                posts = db_sess.query(Posts).filter(Posts.parent_post == post_id)
                return render_template("post.html", board=board_obj, the_post=post_obj, posts=posts,
                                       posts_count=posts.count())
        return render_template("404.html")
    elif request.method == 'POST':
        post = Posts()
        post.time = datetime.datetime.now()
        post.parent_post = post_id
        post.topic = request.form["topic"]
        post.text = request.form["text"]
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = "".join([random.choice([
                "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"
            ]) for _ in range(16)]) + secure_filename(file.filename)
            print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.media = filename
            post.media_type = filename.rsplit('.', 1)[1]
        post.board_name = board_name
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        return redirect(post_id)


@app.errorhandler(404)
def error404(e):
    return render_template("404.html")


def main():
    db_session.global_init("db/imageboard.db")
    app.run(host="0.0.0.0")


if __name__ == '__main__':
    main()
