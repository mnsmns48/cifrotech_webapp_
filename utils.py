import os
import emoji


def sanitize_emoji(text):
    return emoji.replace_emoji(text, replace='')


def connect_all_css():
    css_folder = os.path.join("static", "css")
    css_files = [f"css/{file}" for file in os.listdir(css_folder) if file.endswith(".css")]
    return {'all_css': css_files}


all_css = connect_all_css()
