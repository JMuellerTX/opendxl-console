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

    for i in range(MonitorModule.MAX_PENDING_MESSAGES + 10):
        monitor.queue_message("msg-{}".format(i), "c-bounded")
    bounded = monitor.drain_messages("c-bounded")
    assert len(bounded) == MonitorModule.MAX_PENDING_MESSAGES
    assert bounded[0] == "msg-10"


def test_static_file_handler_prevents_path_traversal(tmp_path):
    import os
    import pytest
    from tornado.web import HTTPError
    from dxlconsole.console import ConsoleStaticFileRequestHandler
    from dxlconsole._resources import resource_filename

    handler = ConsoleStaticFileRequestHandler.__new__(
        ConsoleStaticFileRequestHandler
    )
    web_root = os.path.realpath(resource_filename("dxlconsole", "web"))
    favicon_path = os.path.join(web_root, "images", "favicon.ico")
    assert handler.validate_absolute_path("", favicon_path) == os.path.realpath(
        favicon_path
    )

    with pytest.raises(HTTPError) as exc_info:
        handler.validate_absolute_path("", str(tmp_path / "secret.txt"))
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPError) as exc_info:
        handler.validate_absolute_path(
            "", os.path.join(web_root, "..", "console.py")
        )
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPError) as exc_info:
        handler.validate_absolute_path("", web_root)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPError) as exc_info:
        handler.validate_absolute_path(
            "", os.path.join(web_root, "nonexistent.file")
        )
    assert exc_info.value.status_code == 404


def test_cert_subject_sanitization():
    import pytest
    from dxlconsole.modules.certificates.module import GenerateCertHandler

    for bad_cn in ("../evil", "a/b", "a\\b", "bad\x00cn", "bad\ncn", ""):
        with pytest.raises(Exception):
            GenerateCertHandler._generate_subject_str_from_request(
                {"cn": bad_cn}
            )

    subj = GenerateCertHandler._generate_subject_str_from_request(
        {
            "cn": "valid-client",
            "email": "user-email/CN=injected\r\n",
            "country": "US",
            "state": "CA/O=injected",
            "locality": "SJ\x00",
            "org": "Org/OU=evil",
            "ou": "Unit\n",
        }
    )
    assert subj == (
        "/emailAddress=user-emailCN=injected/CN=valid-client"
        "/C=US/ST=CAO=injected/L=SJ/O=OrgOU=evil/OU=Unit"
    )

    empty_opts_subj = GenerateCertHandler._generate_subject_str_from_request(
        {
            "cn": "valid-client",
            "email": "",
            "country": "",
            "state": "   ",
            "locality": "",
            "org": "",
            "ou": "",
        }
    )
    assert empty_opts_subj == "/CN=valid-client"


def test_topology_broker_registry_escapes_client_id():
    import json
    from dxlclient.message import ErrorResponse, Request
    from dxlconsole.modules.topology.module import TopologyModule

    captured = []

    class FakeClient(object):
        def sync_request(self, req, timeout):
            captured.append(req.payload)
            return ErrorResponse(Request("/test"), error_code=1, error_message="err")

    class FakeApp(object):
        dxl_service_client = FakeClient()

    topo = TopologyModule.__new__(TopologyModule)
    topo._app = FakeApp()
    inj = '"} , "injected": "1'
    topo.get_broker_registry(inj)
    assert json.loads(captured[0]) == {"brokerGuid": inj}

