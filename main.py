from flask import Flask, request, render_template, redirect
# from werkzeug.utils import secure_filename

# import os

from data import db_session
from data.boards import Boards
from data.posts import Posts

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'static/img/from_users'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ['png', 'jpg', 'jpeg', 'gif']


@app.route("/")
def index():
    db_sess = db_session.create_session()
    boards = db_sess.query(Boards)
    return render_template("index.html", boards=boards, boards_count=boards.count())


@app.route("/<board_name>", methods=['POST', 'GET'])
def board(board_name):
    if request.method == 'GET':
        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        for board_obj in board_select:
            posts = db_sess.query(Posts).filter(Posts.board_name == board_obj.name)
            return render_template("board.html", board=board_obj, posts=posts, posts_count=posts.count())
        return render_template("404.html")
    elif request.method == 'POST':
        post = Posts()
        post.topic = request.form["topic"]
        post.text = request.form["text"]
        # post.media, file = request.form["file"], request.files["file"]
        # if file and allowed_file(file.filename):
        #     filename = secure_filename(file.filename)
        #     file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        post.board_name = board_name
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        return redirect(board_name)


@app.errorhandler(404)
def error404(e):
    return render_template("404.html")


# @app.route("/board/<board_name>/<post_id>")
# def board(board_name, post_id):
#     db_sess = db_session.create_session()
#     post_select = db_sess.query(Posts).filter(Posts.id == post_id, Posts.board_name == board_name)
#     for post_obj in post_select:
#         children_posts = db_sess.query(Posts).filter(Posts.parent_post == post_obj.id)
#         return render_template("board.html", parent_post=post_obj, children_posts=children_posts)
#     return render_template("404.html")


def main():
    db_session.global_init("db/imageboard.db")
    app.run(host="0.0.0.0")


if __name__ == '__main__':
    main()
