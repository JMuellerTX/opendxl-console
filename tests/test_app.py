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


def test_create_cert_sets_broker_and_client_extended_key_usage(monkeypatch):
    from dxlconsole.modules.certificates.module import _BaseCertHandler
    import subprocess

    captured_exts = []

    def fake_call(cmd, stderr=None):
        assert stderr == subprocess.DEVNULL
        ext_idx = cmd.index("-extfile") + 1
        with open(cmd[ext_idx], "r") as f:
            captured_exts.append(f.read())
        return 0

    monkeypatch.setattr("subprocess.call", fake_call)

    class DummyFile(object):
        name = "dummy"

    _BaseCertHandler._create_cert(
        DummyFile(), DummyFile(), "ca.crt", "ca.key", "pw", config_type="client"
    )
    _BaseCertHandler._create_cert(
        DummyFile(), DummyFile(), "ca.crt", "ca.key", "pw", config_type="broker"
    )

    assert "extendedKeyUsage=clientAuth\n" in captured_exts[0]
    assert "extendedKeyUsage=serverAuth,clientAuth\n" in captured_exts[1]


def test_send_web_socket_message_ignores_unknown_client():
    from dxlconsole.console import WebConsole

    console = WebConsole.__new__(WebConsole)
    console._web_socket_dict = {}
    # Should not raise KeyError when client_id is absent
    console.send_web_socket_message("unknown-client", "hello")


def test_monitor_drain_messages_and_bounded_topic_cache():
    from collections import OrderedDict
    from dxlclient.message import Response
    from dxlconsole.modules.monitor.module import MonitorModule

    monitor = MonitorModule.__new__(MonitorModule)
    monitor._pending_messages = {}
    monitor._message_id_topics = OrderedDict()

    monitor.queue_message("m1", "c1")
    monitor.queue_message("m2", "c1")
    drained = monitor.drain_messages("c1")
    assert drained == ["m1", "m2"]
    assert monitor.drain_messages("c1") == []

    for i in range(MonitorModule.MAX_MESSAGE_ID_TOPICS + 5):
        monitor.record_message_topic("id-{}".format(i), "/topic/{}".format(i))

    assert len(monitor.message_id_topics) == MonitorModule.MAX_MESSAGE_ID_TOPICS
    assert "id-0" not in monitor.message_id_topics

    resp = Response(request=None)
    resp._request_message_id = "id-{}".format(MonitorModule.MAX_MESSAGE_ID_TOPICS + 4)
    assert monitor.get_message_topic(resp) == "/topic/{}".format(
        MonitorModule.MAX_MESSAGE_ID_TOPICS + 4
    )
    assert resp.request_message_id not in monitor.message_id_topics
