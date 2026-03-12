#!/usr/bin/env python3
"""CGI 示例脚本：根据 query string 返回带颜色的 HTML"""
import os
import urllib.parse

query = os.environ.get("QUERY_STRING", "")
params = urllib.parse.parse_qs(query)
color = params.get("color", ["#f0f0f0"])[0]
name = params.get("name", ["World"])[0]

print("Content-Type: text/html")
print()
print(f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>CGI Color</title></head>
<body style="background-color: {color};">
    <h1>Hello, {name}!</h1>
    <p>背景色: {color}</p>
    <p>CGI 运行正常 ✅</p>
</body>
</html>""")
