import urllib3
import os


http = urllib3.PoolManager()


def download_file(url, file_path):
    stdout = open(file_path, "wb")
    response = http.request("GET", url, preload_content=False)
    for chunk in response.stream(1024):
        stdout.write(chunk)
    response.release_conn()

    if response.status == 404:
        os.remove(file_path)
        return None
