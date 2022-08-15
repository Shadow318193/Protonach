from flask import Flask, request, render_template, redirect, abort, session

from captcha.image import ImageCaptcha
from clear_captcha import clear_captcha

from random import choice

from threading import Timer

import time

import os

import datetime

from data import db_session
from data.boards import Boards
from data.posts import Posts
from data.users import Users

# CONFIGURATION
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'static/media/from_users'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

IMAGE_FILES = ["png", "jpg", "jpeg", "gif", "jfif", "pjpeg", "pjp", "jpe", "webp"]
VIDEO_FILES = ["webm", "mp4", "m4v"]
AUDIO_FILES = ["mp3", "wav"]

PICS_403 = ["gandalf.jpg"]
PICS_404 = ["mario.gif"]
PICS_413 = ["too_cool_and_dangerous.gif", "over9000.png"]

CAPTCHA_MIN_TIME = 5

ALLOWED_FILES = IMAGE_FILES + VIDEO_FILES + AUDIO_FILES
MAX_MEDIA_COUNT = 4

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

# For correct work of captcha.
captcha_for_ip = {}

# Password for admins.
admin_password = "".join([choice(
    ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"]
) for _ in range(16)])


def check_admin(ip):
    db_sess = db_session.create_session()
    user = db_sess.query(Users).filter(Users.ip == ip)
    for u in user:
        return u.admin_level
    return 0


def check_ban(ip):
    db_sess = db_session.create_session()
    user = db_sess.query(Users).filter(Users.ip == ip)
    for u in user:
        return u.is_banned
    return False


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_FILES


def clear_captcha_from_ip(ip):
    if ip in captcha_for_ip:
        if os.path.isfile(f"static/media/captchas/{captcha_for_ip[ip][0]}.png"):
            os.remove(f"static/media/captchas/{captcha_for_ip.pop(ip)[0]}.png")


def generate_new_captcha(ip):
    clear_captcha_from_ip(ip)
    captcha_for_ip[ip] = ("".join([choice(
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]) for _ in range(6)]),
        time.time())
    image = ImageCaptcha(width=280, height=90)
    image.generate(captcha_for_ip[ip][0])
    image.write(captcha_for_ip[ip][0], f"static/media/captchas/{captcha_for_ip[ip][0]}.png")
    print("Сгенерирована новая капча")


def get_ip():
    if PYTHONANYWHERE:
        return request.headers['X-Real-IP']
    return request.remote_addr


def clear_cookies():
    if "topic" in session:
        session.pop("topic")
    if "text" in session:
        session.pop("text")


def post_method(ip, form, files, board_name, post_id=None):
    if post_id == None:
        link = board_name
    else:
        link = post_id

    if check_ban(ip):
        session["message"] = "Доброго времени суток. C вашего IP больше нельзя постить, потому что там " \
                             "завёлся нехороший чувак. Спасибо за сотрудничество, оставайтесь анонимом."
        return link

    for elem in form:
        session[elem] = form[elem]

    if ip not in captcha_for_ip:
        session["message"] = "Извините, но произошли неполадки с капчей. Попробуйте отправить ваше сообщение " \
                             "ещё раз."
        return link

    if "like" in form:
        db_sess = db_session.create_session()
        post = db_sess.query(Posts).filter(Posts.id == form["like"])
        for p in post:
            if ip not in p.raters_like and ip not in p.raters_dislike:
                p.likes += 1
                if p.raters_like:
                    raters = p.raters_like.split(";")
                    raters.append(ip)
                    p.raters_like = ";".join(raters)
                else:
                    p.raters_like = ip
                session["message"] = "Вы поставили лайк."
                print(f"С устройства под IP {ip} был оставлен лайк посту под ID {p.id}")
            else:
                session["message"] = "Вы уже поставили оценку."
        db_sess.commit()
        return link
    elif "dislike" in form:
        db_sess = db_session.create_session()
        post = db_sess.query(Posts).filter(Posts.id == form["dislike"])
        for p in post:
            if ip not in p.raters_like and ip not in p.raters_dislike:
                p.dislikes += 1
                if p.raters_dislike:
                    raters = p.raters_dislike.split(";")
                    raters.append(ip)
                    p.raters_dislike = ";".join(raters)
                else:
                    p.raters_dislike = ip
                session["message"] = "Вы поставили дизлайк."
                print(f"С устройства под IP {ip} был оставлен дизлайк посту под ID {p.id}")
            else:
                session["message"] = "Вы уже поставили оценку."
        db_sess.commit()
        return link

    elif "delete_post" in form:
        if check_admin(ip):
            db_sess = db_session.create_session()
            posts = db_sess.query(Posts).filter(
                (Posts.parent_post == form["delete_post"]) |
                (Posts.id == form["delete_post"]))
            if posts:
                parent_post = False
                for p in posts:
                    if not p.parent_post:
                        parent_post = True
                    for currentdir, dirs, files in os.walk("static/media/from_users"):
                        for f in files:
                            if p.media != None:
                                if f in p.media.split(", ") and os.path.isfile(f"static/media/from_users/{f}"):
                                    print(f)
                                    os.remove(f"static/media/from_users/{f}")
                    db_sess.delete(p)
                db_sess.commit()
                session["message"] = "Вы удалили пост."
                print(f"Админом {ip} был удалён пост под ID {form['delete_post']}")
                if parent_post:
                    return f"/{board_name}"
                return link
            else:
                return "error-404"
        else:
            session["message"] = "Вы не админ."
        return link
    elif "ban" in form:
        if check_admin(ip):
            db_sess = db_session.create_session()
            post = db_sess.query(Posts).filter(Posts.id == form["ban"])
            for p in post:
                user = db_sess.query(Users).filter(Users.ip == p.poster)
                for u in user:
                    if not u.is_banned:
                        if check_admin(p.poster) < check_admin(ip):
                            u.is_banned = 1
                            db_sess.commit()
                            session["message"] = "Вы забанили постера."
                            print(f"Админ {ip} дал бан постеру {p.poster}")
                        else:
                            session["message"] = "Вы пытались забанить админа, равного или " \
                                                 "высшего по уровню. Так нельзя."
                            return link
                    else:
                        session["message"] = "Постер уже забанен."
                        return link
                u = Users()
                u.ip = p.poster
                u.is_banned = 1
                db_sess.add(u)
                db_sess.commit()
                session["message"] = "Вы забанили постера."
                print(f"Админ {ip} дал бан постеру {p.poster}")
        else:
            session["message"] = "Вы не админ."
        return link

    files_list = files.getlist("file[]")
    print(files_list, "!!!", len(files_list))

    if form["captcha"] != captcha_for_ip[ip][0]:
        session["message"] = "Пост не отправлен: капча заполнена неправильно."
        return link
    elif time.time() - captcha_for_ip[ip][1] < CAPTCHA_MIN_TIME:
        session["message"] = "Вы слишком быстро ввели капчу, поэтому сервер посчитал, что вы бот. " \
                             "Попробуйте ввести ещё раз, но медленнее."
        return link
    elif not (form["topic"] or form["text"] or files["file[]"]):
        session["message"] = "Пост не отправлен: ничего не заполнено."
        return link
    elif len(files_list) > MAX_MEDIA_COUNT:
        session["message"] = "Пост не отправлен: нельзя отправить более 4 файлов."
        return link
    elif form["text"] == f"/admin-{admin_password}":
        db_sess = db_session.create_session()
        user = db_sess.query(Users).filter(Users.ip == ip)
        for u in user:
            if check_admin(ip):
                session["message"] = "Вы уже админ."
                clear_cookies()
                return link
            else:
                u.admin_level = 1
                db_sess.commit()
                print(f"{ip} получил админку с помощью команды")
                session["message"] = "Админка получена успешно."
                clear_cookies()
                return link
        user = Users()
        user.ip = ip
        user.admin_level = 1
        db_sess = db_session.create_session()
        db_sess.add(user)
        db_sess.commit()
        print(f"{ip} получил админку с помощью команды")
        session["message"] = "Админка получена успешно."
        clear_cookies()
        return link
    elif "/admin-" in form["text"]:
        session["message"] = "Неправильный пароль."
        return link
    db_sess = db_session.create_session()
    if post_id != None and not db_sess.query(Posts).filter(Posts.id == post_id):
        return "error-404"
    post = Posts()
    post.time = datetime.datetime.now()
    post.time_to_show = str(post.time)[:19]
    post.poster = ip
    if post_id != None:
        post.parent_post = post_id
    post.topic = form["topic"]
    post.text = form["text"]

    f_count = 0
    media = []
    media_type = []
    media_name = []
    for file in files_list:
        print(file)
        if allowed_file(file.filename):
            filename = str(post.time).replace(" ", "-").replace(".", "-").replace(":", "-").lower() + \
                       "_" + str(f_count) + "." + file.filename.rsplit('.', 1)[1].lower()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            media.append(filename)
            media_type.append(filename.rsplit('.', 1)[1].lower())
            media_name.append(file.filename)
            f_count += 1
    if media:
        post.media = ", ".join(media)
    if media_type:
        post.media_type = ", ".join(media_type)
    if media_name:
        post.media_name = ", ".join(media_name)
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
    if post_id != None:
        print(f"Является ответом на пост под ID {post.parent_post}")

    generate_new_captcha(ip)
    session["message"] = "Пост успешно отправлен."
    clear_cookies()
    if post_id == None:
        return link + "/" + str(post.id)
    else:
        return link


@app.route("/")
def index():
    ip = get_ip()
    if "message" in session:
        session.pop("message")
    clear_captcha_from_ip(ip)
    db_sess = db_session.create_session()
    boards = db_sess.query(Boards)
    posts = {}
    for board in boards:
        posts[board.name] = db_sess.query(Posts).filter(Posts.board_name == board.name).count()
    return render_template("index.html", boards=boards, boards_count=boards.count(), posts=posts,
                           from_admin=check_admin(ip))


@app.route("/robots.txt")
def robots():
    ip = get_ip()
    if "message" in session:
        session.pop("message")
    clear_captcha_from_ip(ip)
    return f"{open('robots.txt', 'r').read()}"


@app.route("/admin", methods=['POST', 'GET'])
def admin_menu():
    ip = get_ip()
    clear_captcha_from_ip(ip)

    if request.method == "GET":
        if check_admin(ip) and not check_ban(ip):
            db_sess = db_session.create_session()
            admins = db_sess.query(Users).filter(Users.admin_level > 0, Users.ip != ip)
            users = db_sess.query(Users).filter(Users.admin_level == 0)
            return render_template("admin.html", admins=admins, admins_count=admins.count(),
                                   users=users, users_count=users.count(), you=check_admin(ip),
                                   message=session["message"] if "message" in session else "")
        else:
            return abort(403)

    elif request.method == "POST":
        if check_admin(ip) and not check_ban(ip):
            if "ban" in request.form:
                db_sess = db_session.create_session()
                user = db_sess.query(Users).filter(Users.ip == request.form["ban"])
                for u in user:
                    if not u.is_banned:
                        if check_admin(request.form["ban"]) < check_admin(ip):
                            u.is_banned = 1
                            db_sess.commit()
                            session["message"] = "Вы забанили пользователя."
                            print(f"Админ {ip} дал бан пользователю {request.form['ban']}")
                            return redirect("/admin")
                        else:
                            session["message"] = "Вы пытались забанить админа, равного или " \
                                                 "высшего по уровню. Так нельзя."
                            return redirect("/admin")
                    else:
                        session["message"] = "Пользователь уже забанен."
                        return redirect("/admin")
                session["message"] = "Пользователя нет в списке. Вы играетесь с HTML страницы? :)"
            elif "unban" in request.form:
                db_sess = db_session.create_session()
                user = db_sess.query(Users).filter(Users.ip == request.form["unban"])
                for u in user:
                    if u.is_banned:
                        if check_admin(request.form["unban"]) < check_admin(ip):
                            u.is_banned = 0
                            db_sess.commit()
                            session["message"] = "Вы разбанили пользователя."
                            print(f"Админ {ip} разбанил пользователя {request.form['unban']}")
                            return redirect("/admin")
                        else:
                            session["message"] = "Вы пытались разбанить админа, равного или " \
                                                 "высшего по уровню. Так нельзя."
                            return redirect("/admin")
                    else:
                        session["message"] = "Пользователь уже разбанен."
                        return redirect("/admin")
                session["message"] = "Пользователя нет в списке. Вы играетесь с HTML страницы? :)"
            elif "remove_admin" in request.form:
                db_sess = db_session.create_session()
                user = db_sess.query(Users).filter(Users.ip == request.form["remove_admin"])
                for u in user:
                    if u.admin_level:
                        if check_admin(request.form["remove_admin"]) < check_admin(ip):
                            u.admin_level = 0
                            db_sess.commit()
                            session["message"] = "Вы отобрали админку у пользователя."
                            print(f"Админ {ip} отобрал админку у {request.form['remove_admin']}")
                            return redirect("/admin")
                        else:
                            session["message"] = "Вы пытались уволить админа, равного или " \
                                                 "высшего по уровню. Так нельзя."
                            return redirect("/admin")
                    else:
                        session["message"] = "Пользователь уже уволен."
                        return redirect("/admin")
                session["message"] = "Пользователя нет в списке. Вы играетесь с HTML страницы? :)"
        else:
            return redirect("/admin")



@app.route("/<board_name>", methods=['POST', 'GET'])
def board_url(board_name):
    ip = get_ip()

    if request.method == 'GET':
        generate_new_captcha(ip)

        for elem in request.form:
            session[elem] = request.form[elem]

        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        for board_obj in board_select:
            posts = db_sess.query(Posts).filter(Posts.board_name == board_obj.name,
                                                Posts.parent_post == None)
            post_answers = {}
            post_media = {}
            post_media_type = {}
            post_media_name = {}
            post_media_count = {}
            for post in posts:
                post_answers[post.id] = db_sess.query(Posts).filter(Posts.parent_post == post.id).count()
                if post.media:
                    post_media[post.id] = post.media.split(", ")
                    post_media_type[post.id] = post.media_type.split(", ")
                    post_media_name[post.id] = post.media_name.split(", ")
                    post_media_count[post.id] = len(post.media.split(", "))

            return render_template("board.html", board=board_obj, posts=posts, posts_count=posts.count(),
                                   post_answers=post_answers, post_media=post_media,
                                   post_media_type=post_media_type, post_media_name=post_media_name,
                                   post_media_count=post_media_count,
                                   image_files=IMAGE_FILES, video_files=VIDEO_FILES,
                                   audio_files=AUDIO_FILES, accept_files=accept,
                                   captcha=f"/static/media/captchas/{captcha_for_ip[ip][0]}.png",
                                   from_admin=check_admin(ip), zone=zone,
                                   message=session["message"] if "message" in session else "",
                                   topic=session["topic"] if "topic" in session else "",
                                   text=session["text"] if "text" in session else "", ip=ip,
                                   max_size=app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
                                   max_count=MAX_MEDIA_COUNT)

        return abort(404)
    elif request.method == 'POST':
        link = post_method(ip, request.form, request.files, board_name)
        if "error" in link:
            return abort(int(link.split("-")[1]))
        return redirect(link)


@app.route("/<board_name>/<post_id>", methods=['POST', 'GET'])
def post_url(board_name, post_id):
    ip = get_ip()

    if request.method == 'GET':
        generate_new_captcha(ip)

        for elem in request.form:
            session[elem] = request.form[elem]

        db_sess = db_session.create_session()
        board_select = db_sess.query(Boards).filter(Boards.name == board_name)
        post_select = db_sess.query(Posts).filter(Posts.id == post_id,
                                                  Posts.board_name == board_name,
                                                  Posts.parent_post == None)
        for board_obj in board_select:
            for post_obj in post_select:
                posts = db_sess.query(Posts).filter(Posts.parent_post == post_id)

                if post_obj.media:
                    the_post_media = post_obj.media.split(", ")
                    the_post_media_type = post_obj.media_type.split(", ")
                    the_post_media_name = post_obj.media_name.split(", ")
                    the_post_media_count = len(post_obj.media.split(", "))
                else:
                    the_post_media = None
                    the_post_media_type = None
                    the_post_media_name = None
                    the_post_media_count = None

                post_media = {}
                post_media_type = {}
                post_media_name = {}
                post_media_count = {}
                for post in posts:
                    if post.media:
                        post_media[post.id] = post.media.split(", ")
                        post_media_type[post.id] = post.media_type.split(", ")
                        post_media_name[post.id] = post.media_name.split(", ")
                        post_media_count[post.id] = len(post.media.split(", "))

                return render_template("post.html", board=board_obj, the_post=post_obj, the_post_media=the_post_media,
                                       the_post_media_type=the_post_media_type,
                                       the_post_media_name=the_post_media_name,
                                       the_post_media_count=the_post_media_count, posts=posts,
                                       post_media=post_media, post_media_type=post_media_type,
                                       post_media_name=post_media_name, post_media_count=post_media_count,
                                       posts_count=posts.count(), image_files=IMAGE_FILES, video_files=VIDEO_FILES,
                                       audio_files=AUDIO_FILES, accept_files=accept,
                                       captcha=f"/static/media/captchas/{captcha_for_ip[ip][0]}.png",
                                       from_admin=check_admin(ip), zone=zone,
                                       message=session["message"] if "message" in session else "",
                                       topic=session["topic"] if "topic" in session else "",
                                       text=session["text"] if "text" in session else "", ip=ip,
                                       max_size=app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
                                       max_count=MAX_MEDIA_COUNT)

        return abort(404)
    elif request.method == 'POST':
        link = post_method(ip, request.form, request.files, board_name, post_id)
        if "error" in link:
            return abort(int(link.split("-")[1]))
        return redirect(link)


@app.errorhandler(403)
def error404(e):
    ip = get_ip()
    clear_captcha_from_ip(ip)
    print(e)
    return render_template("error.html", code=403, from_admin=check_admin(ip),
                           text="НЕ админам сюда не пройти. Так Гендальф сказал.",
                           pics=PICS_403)


@app.errorhandler(404)
def error404(e):
    ip = get_ip()
    clear_captcha_from_ip(ip)
    print(e)
    return render_template("error.html", code=404, from_admin=check_admin(ip),
                           text="К сожалению, данный материал больше недоступен или его не существует.",
                           pics=PICS_404)


@app.errorhandler(413)
def error413(e):
    ip = get_ip()
    clear_captcha_from_ip(ip)
    print(e)
    return render_template("error.html", code=413, from_admin=check_admin(ip),
                           text="Извините, но прикреплённый файл оказался по размерам слишком крут "
                                "и опасен для сервера, поэтому сервер подписал отказ в отправке.",
                           pics=PICS_413)


@app.errorhandler(500)
def error500(e):
    ip = get_ip()
    clear_captcha_from_ip(ip)
    print(e)
    return render_template("error.html", code=500, from_admin=check_admin(ip),
                           text="По причинческим технинам сервер подписал отказ. "
                                "Извините за доставленные неудобства.",
                           pics=["prichincheskaya_tehnina.png"])


print(admin_password)
if not PYTHONANYWHERE:
    zone = "МСК"


    def main():
        db_session.global_init("db/imageboard.db")
        clear_captcha()
        timer = RepeatTimer(2 * 60, clear_captcha)
        timer.start()
        app.run(host="0.0.0.0")


    if __name__ == '__main__':
        main()
else:
    zone = "UTC"
    db_session.global_init("db/imageboard.db")
    clear_captcha()
