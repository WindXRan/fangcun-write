"""启动本地服务器（UTF-8编码支持）"""
import http.server
import socketserver
import os

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 设置正确的编码
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
    
    def guess_type(self, path):
        # 为JSON文件设置正确的Content-Type
        if path.endswith('.json'):
            return 'application/json; charset=utf-8'
        return super().guess_type(path)

PORT = 8000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

with socketserver.TCPServer(('', PORT), MyHandler) as httpd:
    print(f'服务器启动: http://localhost:{PORT}')
    print(f'书库页面: http://localhost:{PORT}/library.html')
    print(f'扫榜页面: http://localhost:{PORT}/index.html')
    httpd.serve_forever()
