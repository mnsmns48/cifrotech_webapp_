import boto3
from botocore.exceptions import NoCredentialsError, EndpointConnectionError, ClientError

from config import Settings, settings


async def download_image(session, url, save_path):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(save_path, "wb") as file:
                    file.write(await response.read())
    except Exception as e:
        print(f"Error {url}: {e}")


# async def callable_func_(pic_urls: list, session: ClientSession, origin: str):
#     tasks = list()
#     for url in image_urls:
#         tasks.append(download_image(session, url, f"images/{url.rsplit('/', 1)[1]}"))
#     await asyncio.gather(*tasks)


async def callable_func_():
    print('ok')


async def check_s3_connection():
    print(repr(settings.s3.s3_access_key))
    try:
        session = boto3.session.Session(
            aws_access_key_id=settings.s3.s3_access_key,
            aws_secret_access_key=settings.s3.s3_secret_access_key,
            region_name=settings.s3.region,
        )
        s3 = session.resource('s3', endpoint_url=settings.s3.s3_url)
        bucket = s3.Bucket(settings.s3.bucket_name)
        objects = list(bucket.objects.limit(1))
        return True
    except (NoCredentialsError, EndpointConnectionError):
        return False
    except ClientError as e:
        return False


def list_objects(prefix: str):
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3.s3_url.rstrip("/"),
        aws_access_key_id=settings.s3.s3_access_key.strip(),
        aws_secret_access_key=settings.s3.s3_secret_access_key.strip(),
        region_name=settings.s3.region
    )

    try:
        resp = s3.list_objects_v2(
            Bucket=settings.s3.bucket_name,
            Prefix=prefix
        )
        contents = resp.get("Contents", [])
        keys = [obj["Key"] for obj in contents]
        print("Found keys:", keys)
        return keys

    except ClientError as e:
        code = e.response["Error"].get("Code")
        print(f"❌ list_objects_v2 failed: {code}")
        return []
