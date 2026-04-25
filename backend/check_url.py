import urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8022/", timeout=5) as resp:
        print("URL:", resp.geturl())
        print("STATUS:", resp.status)
except Exception as e:
    if hasattr(e, "geturl"): print("URL:", e.geturl())
    if hasattr(e, "code"): print("STATUS:", e.code)
    else: print("ERR:", e)