from config import settings


def get_pathname_icon_url(icon: str) -> str:
    s3 = settings.s3
    base_url = s3.s3_url.removeprefix("https://").rstrip("/")
    return f"https://{s3.bucket_name}.{base_url}/{s3.s3_hub_prefix}/{s3.utils_path}/{icon}"
