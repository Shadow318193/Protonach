from flask import Flask, request, render_template, redirect
from captcha.image import ImageCaptcha
from random import choice

import os
from threading import Timer

from data import db_session
from data.boards import Boards
from data.posts import Posts

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'static/media/from_users'
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024

IMAGE_FILES = ["png", "jpg", "jpeg", "gif", "jfif", "pjpeg", "pjp", "jpe", "webp"]
VIDEO_FILES = ["webm", "mp4", "m4v"]
AUDIO_FILES = ["mp3", "wav"]

ALLOWED_FILES = IMAGE_FILES + VIDEO_FILES + AUDIO_FILES


class RepeatTimer(Timer):
    def __init__(self, interval, function, args=None, kwargs=None):
        Timer.__init__(self, interval=interval, function=function, args=args, kwargs=kwargs)

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def make_accept_for_html(mime):
    if mime in IMAGE_FILES:
        return "image/" + mime
    elif mime in VIDEO_FILES:
        return "video/" + mime
    elif mime in AUDIO_FILES:
        return "audio/" + mime


accept = ",".join([make_accept_for_html(x) for x in ALLOWED_FILES])
captcha_for_ip = {}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_FILES


@app.route("/")
def index():
    ip = request.remote_addr
    if ip in captcha_for_ip:
        if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip]}.png"):
            os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)}.png")
    db_sess = db_session.create_session()
    boards = db_sess.query(Boards)
    posts = {}
    for board in boards:
        posts[board.name] = db_sess.query(Posts).filter(Posts.board_name == board.name).count()
    return render_template("index.html", boards=boards, boards_count=boards.count(), posts=posts)


@app.route("/robots.txt")
def robots():
    ip = request.remote_addr
    if ip in captcha_for_ip:
        if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip]}.png"):
            os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)}.png")
    return f"<pre>{open('robots.txt', 'r').read()}</pre>"


@app.route("/<board_name>", methods=['POST', 'GET'])
def board_url(board_name):
    ip = request.remote_addr
    # ip = request.headers['X-Real-IP']
    # FOR PYTHONANYWHERE.COM
    if request.method == 'GET':
        if ip in captcha_for_ip:
            if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip]}.png"):
                os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)}.png")
        captcha_for_ip[ip] = "".join([choice(
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]) for _ in range(6)])
        image = ImageCaptcha(width=280, height=90)
        image.generate(captcha_for_ip[ip])
        image.write(captcha_for_ip[ip], f"static/media/captchas/{captcha_for_ip[ip]}.png")
        print("Сгенерирована новая каптча")
        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        for board_obj in board_select:
            posts = db_sess.query(Posts).filter(Posts.board_name == board_obj.name,
                                                Posts.parent_post == None)
            post_answers = {}
            for post in posts:
                post_answers[post.id] = db_sess.query(Posts).filter(Posts.parent_post == post.id).count()
            return render_template("board.html", board=board_obj, posts=posts, posts_count=posts.count(),
                                   post_answers=post_answers, image_files=IMAGE_FILES, video_files=VIDEO_FILES,
                                   audio_files=AUDIO_FILES, accept_files=accept,
                                   captcha=f"/static/media/captchas/{captcha_for_ip[ip]}.png")
        return render_template("error.html", code=404,
                               text="К сожалению, данная доска больше недоступна или её не существует.",
                               pics=["crab-rave.gif", "mario.gif"])
    elif request.method == 'POST':
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
                    print(f"С устройства с IP {ip} был оставлен лайк на посте с ID {p.id}:")
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
                    print(f"С устройства с IP {ip} был оставлен дизлайк на посте с ID {p.id}:")
            db_sess.commit()
            return redirect(board_name)
        if not (request.form["topic"] or request.form["text"] or request.files["file"]) \
                or request.form["captcha"] != captcha_for_ip[ip]:
            return redirect(board_name)
        post = Posts()
        post.poster = ip
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
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        print(f"С устройства с IP {ip} было отправлено сообщение следующего содержания:")
        print(f"ID поста: {post.id}")
        print(f"Заголовок: {post.topic}")
        print(f"Основной текст: {post.text}")
        print(f"Медиа: {post.media_name}")
        print(f"Время: {post.time}")
        if ip in captcha_for_ip:
            if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip]}.png"):
                os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)}.png")
        captcha_for_ip[ip] = "".join([choice(
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]) for _ in range(6)])
        image = ImageCaptcha(width=280, height=90)
        image.generate(captcha_for_ip[ip])
        image.write(captcha_for_ip[ip], f"static/media/captchas/{captcha_for_ip[ip]}.png")
        print("Сгенерирована новая каптча")
        return redirect(board_name + "/" + str(post.id))


@app.route("/<board_name>/<post_id>", methods=['POST', 'GET'])
def post_url(board_name, post_id):
    ip = request.remote_addr
    # ip = request.headers['X-Real-IP']
    # FOR PYTHONANYWHERE.COM
    if request.method == 'GET':
        if ip in captcha_for_ip:
            if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip]}.png"):
                os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)}.png")
        captcha_for_ip[ip] = "".join([choice(
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]) for _ in range(6)])
        image = ImageCaptcha(width=280, height=90)
        image.generate(captcha_for_ip[ip])
        image.write(captcha_for_ip[ip], f"static/media/captchas/{captcha_for_ip[ip]}.png")
        print("Сгенерирована новая каптча")
        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        post_select = db_sess.query(Posts).filter(Posts.id == post_id,
                                                  Posts.board_name == board_name,
                                                  Posts.parent_post == None)
        for board_obj in board_select:
            for post_obj in post_select:
                posts = db_sess.query(Posts).filter(Posts.parent_post == post_id)
                return render_template("post.html", board=board_obj, the_post=post_obj, posts=posts,
                                       posts_count=posts.count(), image_files=IMAGE_FILES, video_files=VIDEO_FILES,
                                       audio_files=AUDIO_FILES, accept_files=accept,
                                       captcha=f"/static/media/captchas/{captcha_for_ip[ip]}.png")
        return render_template("error.html", code=404,
                               text="К сожалению, данный тред больше недоступен или его не существует.",
                               pics=["crab-rave.gif", "mario.gif"])
    elif request.method == 'POST':
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
                    print(f"С устройства с IP {ip} был оставлен лайк на посте с ID {p.id}:")
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
                    print(f"С устройства с IP {ip} был оставлен дизлайк на посте с ID {p.id}:")
            db_sess.commit()
            return redirect(post_id)
        if not (request.form["topic"] or request.form["text"] or request.files["file"]) \
                or request.form["captcha"] != captcha_for_ip[ip]:
            return redirect(post_id)
        post = Posts()
        post.poster = ip
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
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        print(f"С устройства с IP {ip} было отправлено сообщение следующего содержания:")
        print(f"ID поста: {post.id}")
        print(f"Заголовок: {post.topic}")
        print(f"Основной текст: {post.text}")
        print(f"Медиа: {post.media_name}")
        print(f"Время: {post.time}")
        print(f"Является ответом на пост с ID {post.parent_post}")
        if ip in captcha_for_ip:
            if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip]}.png"):
                os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)}.png")
        captcha_for_ip[ip] = "".join([choice(
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]) for _ in range(6)])
        image = ImageCaptcha(width=280, height=90)
        image.generate(captcha_for_ip[ip])
        image.write(captcha_for_ip[ip], f"static/media/captchas/{captcha_for_ip[ip]}.png")
        print("Сгенерирована новая каптча")
        return redirect(post_id)


@app.errorhandler(404)
def error404(e):
    print(e)
    return render_template("error.html", code=404,
                           text="К сожалению, данный материал больше недоступен или его не существует.",
                           pics=["crab-rave.gif", "mario.gif"])


@app.errorhandler(413)
def error413(e):
    print(e)
    return render_template("error.html", code=413,
                           text="Извините, но прикреплённый файл оказался по размерам слишком крут "
                                "и опасен для сервера, поэтому сервер подписал отказ в отправке.",
                           pics=["too_cool_and_dangerous.gif", "over9000.png"])


@app.errorhandler(500)
def error500(e):
    print(e)
    return render_template("error.html", code=500,
                           text="По причинческим технинам сервер подписал отказ. "
                                "Извините за доставленные неудобства.",
                           pics=["prichincheskaya_tehnina.png"])


@app.errorhandler(502)
def error502(e):
    print(e)
    return render_template("error.html", code=502,
                           text="По причинческим технинам у сервера разногласия с хостом. "
                                "Извините за доставленные неудобства.",
                           pics=["prichincheskaya_tehnina.png"])


def clean_captcha():
    for currentdir, dirs, files in os.walk("static/media/captchas"):
        for f in files:
            if f != ".gitignore" and os.path.isfile(f"static/media/captchas/{f}"):
                print(f)
                os.remove(f"static/media/captchas/{f}")
    print("Вся каптча почищена")


def main():
    db_session.global_init("db/imageboard.db")
    timer = RepeatTimer(2 * 60, clean_captcha)
    timer.start()
    app.run(host="0.0.0.0")


if __name__ == '__main__':
    main()

# db_session.global_init("db/imageboard.db")
# timer = RepeatTimer(2 * 60, clean_captcha)
# timer.start()
# FOR PYTHONANYWHERE.COM
