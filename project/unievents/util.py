import requests
from pathlib import Path


def download(url, path, chunk=2048):
    try:
        with open(path, "wb") as f:
            download_to_io(url, f, chunk)
    except Exception as e:
        Path(path).unlink()
        raise e


def download_to_io(url, io, chunk=2048):
    req = requests.get(url, stream=True)
    if req.status_code == 200:
        for chunk in req.iter_content(chunk):
            io.write(chunk)
        return io
    raise Exception("Given url returned status code: {}".format(req.status_code))
