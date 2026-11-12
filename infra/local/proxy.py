


import http.client
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
ROTAS = [
    ("/api/usuarios", int(os.environ.get("PORTA_USUARIOS", 3001))),
    ("/api/recursos", int(os.environ.get("PORTA_RECURSOS", 3002))),
    ("/api/reservas", int(os.environ.get("PORTA_RESERVAS", 3003))),
]
PORTA_WEB = int(os.environ.get("PORTA_WEB", 8080))
SALTAR = {"connection", "keep-alive", "transfer-encoding", "upgrade", "proxy-connection", "content-length"}


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _encaminhar(self):
        porta = next((p for prefixo, p in ROTAS if self.path.startswith(prefixo)), PORTA_WEB)
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tamanho) if tamanho else None
        cabecalhos = {k: v for k, v in self.headers.items() if k.lower() not in SALTAR}
        conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=15)
        try:
            conexao.request(self.command, self.path, body=corpo, headers=cabecalhos)
            resposta = conexao.getresponse()
            dados = resposta.read()
        except OSError:
            dados, status, envio = b'{"erro":"bad_gateway"}', 502, [("Content-Type", "application/json")]
        else:
            status = resposta.status
            envio = [(k, v) for k, v in resposta.getheaders() if k.lower() not in SALTAR]
        finally:
            conexao.close()
        self.send_response(status)
        for k, v in envio:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _encaminhar

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    porta = int(os.environ.get("PROXY_PORT", 8000))
    print(f"proxy local em http://{HOST}:{porta}")
    ThreadingHTTPServer((HOST, porta), Proxy).serve_forever()
