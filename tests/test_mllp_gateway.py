import threading

from silhouette_core.pipelines import mllp_gateway


def test_mllp_server_loopback(tmp_path):
    server = mllp_gateway.MLLPServer(('127.0.0.1', 0), mllp_gateway.MLLPHandler, str(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    message = b'MSH|^~\\&|SIL|SIL|EHR|EHR|202402091030||ADT^A01|MSG|P|2.5.1\r'
    ack = mllp_gateway.send(host, port, message)
    server.shutdown()
    thread.join()
    assert ack.startswith(mllp_gateway.START_BLOCK + b'MSH')
    files = list(tmp_path.glob('*.hl7'))
    assert files, 'message not written'
    content = files[0].read_bytes()
    assert message.strip(b'\r') in content
