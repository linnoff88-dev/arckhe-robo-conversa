#!/usr/bin/env python3
"""Servidor Jarvis de MENTIRA, só para testar o robô sem chamar nada de verdade.
Responde a POST /conversa com uma frase fixa e um áudio de 1 s gerado aqui."""
import base64, io, json, math, struct, wave
from http.server import BaseHTTPRequestHandler, HTTPServer


def tom(seg=1.0, hz=220):
    b = io.BytesIO()
    with wave.open(b, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * hz * i / 16000) * (0.5 + 0.5 * math.sin(i / 1500))))
                               for i in range(int(16000 * seg))))
    return b.getvalue()


class H(BaseHTTPRequestHandler):
    visto = []

    def log_message(self, *a): pass

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); d = json.loads(self.rfile.read(n) or b'{}')
        H.visto.append({'texto': d.get('texto'), 'tem_audio': bool(d.get('audio_wav_b64')), 'auth': self.headers.get('Authorization')})
        r = {'ouvido': d.get('texto') or '(áudio)', 'resposta': 'Oi! Eu sou o robô da mesa.', 'audio_wav_b64': base64.b64encode(tom()).decode()}
        b = json.dumps(r).encode(); self.send_response(200); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 8787), H).serve_forever()
