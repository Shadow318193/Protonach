from flask import Flask, request, render_template, redirect, abort

from captcha.image import ImageCaptcha
from clear_captcha import clear_captcha

from random import choice

from threading import Timer

import os

import datetime

from data import db_session
from data.boards import Boards
from data.posts import Posts

# CONFIGURATION
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'static/media/from_users'
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024

IMAGE_FILES = ["png", "jpg", "jpeg", "gif", "jfif", "pjpeg", "pjp", "jpe", "webp"]
VIDEO_FILES = ["webm", "mp4", "m4v"]
AUDIO_FILES = ["mp3", "wav"]

PICS_404 = ["crab-rave.gif", "mario.gif"]
PICS_413 = ["too_cool_and_dangerous.gif", "over9000.png"]

ALLOWED_FILES = IMAGE_FILES + VIDEO_FILES + AUDIO_FILES

PYTHONANYWHERE = False  # http://shadow318193.pythonanywhere.com


# Code start
class RepeatTimer(Timer):
    def __init__(self, interval, function, args=None, kwargs=None):
        Timer.__init__(self, interval=interval, function=function, args=args, kwargs=kwargs)

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def make_accept_for_html(mime):
    # For input tag in HTML
    if mime in IMAGE_FILES:
        return "image/" + mime
    elif mime in VIDEO_FILES:
        return "video/" + mime
    elif mime in AUDIO_FILES:
        return "audio/" + mime


accept = ",".join([make_accept_for_html(x) for x in ALLOWED_FILES])

# For correct work of captcha
captcha_for_ip = {}

# Backdoor
admin_password = "".join([choice(
    ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"]
) for _ in range(16)])

# For admins' ip
admins = {"127.0.0.1"}

# Banned ip: level of ban
banned_ip = set()


def check_admin(ip):
    if ip in admins:
        return True
    return False


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_FILES


def clear_captcha_from_ip(ip):
    if ip in captcha_for_ip:
        if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip]}.png"):
            os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)}.png")


def generate_new_captcha(ip):
    clear_captcha_from_ip(ip)
    captcha_for_ip[ip] = "".join([choice(
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]) for _ in range(6)])
    image = ImageCaptcha(width=280, height=90)
    image.generate(captcha_for_ip[ip])
    image.write(captcha_for_ip[ip], f"static/media/captchas/{captcha_for_ip[ip]}.png")
    print("Сгенерирована новая каптча")


def get_ip():
    if PYTHONANYWHERE:
        return request.headers['X-Real-IP']
    return request.remote_addr


@app.route("/")
def index():
    ip = get_ip()
    clear_captcha_from_ip(ip)
    db_sess = db_session.create_session()
    boards = db_sess.query(Boards)
    posts = {}
    for board in boards:
        posts[board.name] = db_sess.query(Posts).filter(Posts.board_name == board.name).count()
    return render_template("index.html", boards=boards, boards_count=boards.count(), posts=posts)


@app.route("/robots.txt")
def robots():
    ip = get_ip()
    clear_captcha_from_ip(ip)
    return f"{open('robots.txt', 'r').read()}"


@app.route("/<board_name>", methods=['POST', 'GET'])
def board_url(board_name):
    ip = get_ip()

    if request.method == 'GET':
        generate_new_captcha(ip)

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
                                   captcha=f"/static/media/captchas/{captcha_for_ip[ip]}.png",
                                   from_admin=check_admin(ip))

        return abort(404)
    elif request.method == 'POST':
        if ip in banned_ip:
            return redirect(board_name)
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
                    print(f"С устройства под IP {ip} был оставлен лайк посту под ID {p.id}")
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
                    print(f"С устройства под IP {ip} был оставлен дизлайк посту под ID {p.id}")
            db_sess.commit()
            return redirect(board_name)
        elif "delete_post" in request.form:
            if ip in admins:
                db_sess = db_session.create_session()
                posts = db_sess.query(Posts).filter(
                    (Posts.parent_post == request.form["delete_post"]) |
                    (Posts.id == request.form["delete_post"]))
                if posts:
                    for p in posts:
                        for currentdir, dirs, files in os.walk("static/media/from_users"):
                            for f in files:
                                if f == p.media_name and os.path.isfile(f"static/media/from_users/{f}"):
                                    print(f)
                                    os.remove(f"static/media/from_users/{f}")
                        db_sess.delete(p)
                    db_sess.commit()
                    print(f"Админом {ip} был удалён пост под ID {request.form['delete_post']}")
                    return redirect(board_name)
                else:
                    abort(404)
            return redirect(board_name)
        elif "ban" in request.form:
            if ip in admins:
                db_sess = db_session.create_session()
                post = db_sess.query(Posts).filter(Posts.id == request.form["ban"])
                for p in post:
                    if p.poster not in admins:
                        banned_ip.add(p.poster)
            return redirect(board_name)

        if not (request.form["topic"] or request.form["text"] or request.files["file"]) \
                or request.form["captcha"] != captcha_for_ip[ip]:
            return redirect(board_name)
        elif request.form["text"] == f"/admin-{admin_password}":
            admins.add(ip)
            return redirect(board_name)

        post = Posts()
        post.time = datetime.datetime.now()
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

        print(f"С устройства под IP {ip} было отправлено сообщение следующего содержания:")
        print(f"ID поста: {post.id}")
        print(f"Заголовок: {post.topic}")
        print(f"Основной текст: {post.text}")
        print(f"Медиа: {post.media_name}")
        print(f"Время: {post.time}")

        generate_new_captcha(ip)
        return redirect(board_name + "/" + str(post.id))


@app.route("/<board_name>/<post_id>", methods=['POST', 'GET'])
def post_url(board_name, post_id):
    ip = get_ip()

    if request.method == 'GET':
        generate_new_captcha(ip)

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
                                       captcha=f"/static/media/captchas/{captcha_for_ip[ip]}.png",
                                       from_admin=check_admin(ip))

        return abort(404)
    elif request.method == 'POST':
        if ip in banned_ip:
            return redirect(post_id)
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
                    print(f"С устройства под IP {ip} был оставлен лайк посту под ID {p.id}")
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
                    print(f"С устройства под IP {ip} был оставлен дизлайк посту под ID {p.id}")
            db_sess.commit()
            return redirect(post_id)
        elif "delete_post" in request.form:
            if ip in admins:
                db_sess = db_session.create_session()
                posts = db_sess.query(Posts).filter(
                    (Posts.parent_post == request.form["delete_post"]) |
                    (Posts.id == request.form["delete_post"]))
                if posts:
                    parent_post = False
                    for p in posts:
                        if not p.parent_post:
                            parent_post = True
                        for currentdir, dirs, files in os.walk("static/media/from_users"):
                            for f in files:
                                if f == p.media_name and os.path.isfile(f"static/media/from_users/{f}"):
                                    print(f)
                                    os.remove(f"static/media/from_users/{f}")
                        db_sess.delete(p)
                    db_sess.commit()
                    print(f"Админом {ip} был удалён пост под ID {request.form['delete_post']}")
                    if parent_post:
                        return redirect(f"/{board_name}")
                    return redirect(post_id)
                else:
                    abort(404)
            return redirect(post_id)
        elif "ban" in request.form:
            if ip in admins:
                db_sess = db_session.create_session()
                post = db_sess.query(Posts).filter(Posts.id == request.form["ban"])
                for p in post:
                    if p.poster not in admins:
                        banned_ip.add(p.poster)
            return redirect(post_id)

        if not (request.form["topic"] or request.form["text"] or request.files["file"]) \
                or request.form["captcha"] != captcha_for_ip[ip]:
            return redirect(post_id)
        elif request.form["text"] == f"/admin-{admin_password}":
            admins.add(ip)
            return redirect(post_id)
        post = Posts()
        post.time = datetime.datetime.now()
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

        print(f"С устройства под IP {ip} было отправлено сообщение следующего содержания:")
        print(f"ID поста: {post.id}")
        print(f"Заголовок: {post.topic}")
        print(f"Основной текст: {post.text}")
        print(f"Медиа: {post.media_name}")
        print(f"Время: {post.time}")
        print(f"Является ответом на пост под ID {post.parent_post}")

        generate_new_captcha(ip)
        return redirect(post_id)


@app.errorhandler(404)
def error404(e):
    ip = get_ip()
    clear_captcha_from_ip(ip)
    print(e)
    return render_template("error.html", code=404,
                           text="К сожалению, данный материал больше недоступен или его не существует.",
                           pics=PICS_404)


@app.errorhandler(413)
def error413(e):
    ip = get_ip()
    clear_captcha_from_ip(ip)
    print(e)
    return render_template("error.html", code=413,
                           text="Извините, но прикреплённый файл оказался по размерам слишком крут "
                                "и опасен для сервера, поэтому сервер подписал отказ в отправке.",
                           pics=PICS_413)


@app.errorhandler(500)
def error500(e):
    ip = get_ip()
    clear_captcha_from_ip(ip)
    print(e)
    return render_template("error.html", code=500,
                           text="По причинческим технинам сервер подписал отказ. "
                                "Извините за доставленные неудобства.",
                           pics=["prichincheskaya_tehnina.png"])


print(admin_password)
if not PYTHONANYWHERE:
    def main():
        db_session.global_init("db/imageboard.db")
        clear_captcha()
        timer = RepeatTimer(2 * 60, clear_captcha)
        timer.start()
        app.run(host="0.0.0.0")


    if __name__ == '__main__':
        main()
else:
    db_session.global_init("db/imageboard.db")
    clear_captcha()
