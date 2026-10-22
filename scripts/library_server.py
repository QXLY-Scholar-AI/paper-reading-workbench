"""Loopback-only library server with user-triggered system-Recycle-Bin deletion."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import argparse,json,secrets
from library_delete import delete_results

def serve(library,port):
    root=Path(library).resolve();token=secrets.token_urlsafe(32)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(root),**kwargs)
        def end_headers(self):
            self.send_header('Cache-Control','no-cache');super().end_headers()
        def reply(self,status,data):
            body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def allowed_host(self):return self.headers.get('Host') in {f'127.0.0.1:{port}',f'localhost:{port}'}
        def do_GET(self):
            if not self.allowed_host():return self.reply(403,{'error':'仅允许本机访问'})
            if self.path=='/api/config':return self.reply(200,{'token':token,'can_recycle':True})
            path=Path(self.translate_path(self.path)).resolve()
            if path!=root and root not in path.parents:return self.reply(403,{'error':'路径越界'})
            if any(p.startswith('.') for p in path.relative_to(root).parts):return self.reply(403,{'error':'内部文件'})
            return super().do_GET()
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.allowed_host() or origin not in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'} or self.headers.get('X-Workbench-Token')!=token:return self.reply(403,{'error':'请求来源校验失败，请从论文库页面操作'})
            if self.path!='/api/delete':return self.reply(404,{'error':'接口不存在'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<16384:raise ValueError('请求大小无效')
                data=json.loads(self.rfile.read(size));result=delete_results(root,data['paper_id'],data['tasks']);self.reply(200,result)
            except (ValueError,KeyError,OSError,TypeError) as e:self.reply(400,{'error':str(e)})
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--library',required=True);p.add_argument('--port',type=int,default=8768);a=p.parse_args();serve(a.library,a.port)
