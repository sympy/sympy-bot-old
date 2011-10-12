import sys
import logging
import traceback

from django.utils import simplejson as json

class InvalidRequest(Exception):
    pass

class JSONRPCServer(object):

    def __init__(self, methods):
        self._methods = methods

        def describe():
            # FIXME: show system.describe in the method list (after the client
            # side JavaScript is fixed to handle that):
            procs = [{"name": m} for m in self._methods if m != "system.describe"]
            result = {
                    "sdversion": "1.0",
                    "name": "AsyncHandler",
                    "procs": procs,
                    }
            return result

        self._methods["system.describe"] = describe

    def handle_request_from_client(self, data_str):
        data = json.loads(data_str)
        logging.info("JSON RPC in: " + str(data))
        if data["jsonrpc"] != "2.0":
            raise InvalidRequest("JSON RPC version number must be 2.0")
        id = data["id"]
        method = data["method"]
        params = data.get("params", None)
        try:
            if params is None:
                result = self._methods[method]()
            elif len(params) == 0:
                result = self._methods[method]()
            elif isinstance(params, (list, tuple)):
                result = self._methods[method](*params)
            else:
                raise NotImplementedError()
        except:
            etype, value, tb = sys.exc_info()
            s = "".join(traceback.format_exception(etype, value, tb))
            logging.info("Exception raised while running an RPC method\n" + s)
            result = {
                "ok": False,
                "reason": "Unhandled exception.",
                }
        output = {"jsonrpc": "2.0", "id": id, "result": result}
        logging.info("JSON RPC out: " + str(output))
        return json.dumps(output)
