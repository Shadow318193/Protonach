from flask import Flask, url_for, render_template

from data import db_session
from data.boards import Boards

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'


@app.route("/")
def index():
    db_sess = db_session.create_session()
    boards = db_sess.query(Boards)
    return render_template("index.html", boards=boards, boards_count=boards.count())


def main():
    db_session.global_init("db/imageboard.db")
    app.run()


if __name__ == '__main__':
    main()
