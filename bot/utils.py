def filter_keys(data) -> dict:
    keys = ['video', 'photo', 'text', 'caption', 'forward_origin']
    filtered = {key: value for key, value in data.items() if key in keys and value}
    return filtered
