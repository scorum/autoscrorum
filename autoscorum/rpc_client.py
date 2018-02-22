import json
import time
import websocket


class RpcClient(object):
    def __init__(self):
        self._ws = None

    def open_ws(self, addr):
        retries = 0
        error = None
        while retries < 10:
            try:
                self._ws = websocket.create_connection("ws://{addr}".format(addr=addr))
                return
            except ConnectionRefusedError as e:
                error = e
                retries += 1
                time.sleep(0.5)
        raise error

    def close_ws(self):
        if self._ws:
            self._ws.shutdown()

    def send(self, json_request):
        self._ws.send(json_request)
        return json.loads(self._ws.recv())
