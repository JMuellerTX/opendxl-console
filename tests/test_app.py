import hashlib

from dxlconsole.app import OpenDxlConsole


def test_user_cookie_name_without_unique_id(tmp_path):
    app = OpenDxlConsole(str(tmp_path))
    assert app.user_cookie_name == "user"


def test_user_cookie_name_with_unique_id(tmp_path):
    # The broker passes its identifier as a command line argument (a str);
    # hashing it must work on Python 3
    unique_id = "1ddbfa91-c46c-4a63-b3ea-d928c209a9e3"
    app = OpenDxlConsole(str(tmp_path), unique_id)
    expected = hashlib.md5(unique_id.encode("utf-8")).hexdigest()
    assert app.user_cookie_name == expected + "_user"
