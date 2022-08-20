import os


def clear_captcha():
    for currentdir, dirs, files in os.walk("static/media/captchas"):
        for f in files:
            if f != ".gitignore" and os.path.isfile(f"static/media/captchas/{f}"):
                print(f)
                os.remove(f"static/media/captchas/{f}")
    print("Вся каптча почищена")


if __name__ == "__main__":
    clear_captcha()
