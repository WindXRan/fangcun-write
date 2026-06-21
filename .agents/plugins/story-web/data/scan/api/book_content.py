"""书籍内容API"""
import json
import re
import sys
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 项目根目录（硬编码）
ROOT_DIR = Path(r'C:\Users\Administrator\Documents\trae_projects\AI网文小说项目')

class BookAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == '/api/book_content':
            file_path = params.get('file', [None])[0]
            if not file_path:
                self.send_json({"error": "未指定文件"})
                return
            
            # 尝试多种路径
            possible_paths = [
                ROOT_DIR / file_path,
                Path(file_path),
            ]
            
            full_path = None
            for path in possible_paths:
                if path.exists():
                    full_path = path
                    break
            
            if not full_path:
                self.send_json({"error": "文件不存在: " + file_path})
                return
            
            try:
                content = full_path.read_text(encoding='utf-8')
                chapters = self.split_chapters(content)
                
                # 提取书名（第一行或文件名）
                title = full_path.stem
                
                self.send_json({
                    "title": title,
                    "chapters": chapters
                })
            except Exception as e:
                self.send_json({"error": str(e)})
        else:
            self.send_json({"error": "未知API"})
    
    def split_chapters(self, content):
        """将内容拆分为章节"""
        chapters = []
        pattern = r'(第\d+章[^\n]*)'
        parts = re.split(pattern, content)
        
        i = 1
        while i < len(parts):
            title = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ''
            chapters.append({
                'title': title,
                'content': body,
                'char_count': len(re.sub(r'\s', '', body))
            })
            i += 2
        
        return chapters
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # 禁用日志

if __name__ == '__main__':
    PORT = 8001
    server = HTTPServer(('', PORT), BookAPI)
    print(f'书籍API启动: http://localhost:{PORT}')
    server.serve_forever()
