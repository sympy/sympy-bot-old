"""
This example shows how to use the RPC API to upload a test result
"""

import sys
sys.path.append("..")
from jsonrpc import JSONRPCService

url_base = "http://localhost:8080"
s = JSONRPCService(url_base + "/async")
r = s.RPC.upload_task(113, "Passed", "python", "bin/test something",
        """some log\nsomeother log\n and so on\n""")
print r
