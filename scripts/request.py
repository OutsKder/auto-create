import urllib.request
r=urllib.request.urlopen('http://127.0.0.1:8000/api/v1/pipeline/123/stage/analysis/execute/stream?title=test')
for _ in range(5):
 print(r.readline().decode("utf-8"))