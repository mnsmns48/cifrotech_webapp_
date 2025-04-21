import emoji


def sanitize_emoji(text):
    return emoji.replace_emoji(text, replace='')
