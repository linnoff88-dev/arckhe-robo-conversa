#!/usr/bin/env python3
"""Ponte do Robô conversa: roda no Raspberry Pi 3.

Toque na tela → grava a sua voz → manda ao SEU servidor Jarvis → toca a resposta, com o rosto reagindo.
Só biblioteca padrêo do Python 3. Áudio: arecord/aplay (ALSA); voz de reserva: espeak-ng.

  JARVIS_URL    ex.: http://100.64.0.10:8787   (o servidor recebe POST {JARVIS_URL}/conversa)
  JARVIS_TOKEN  opcional; vai em "Authorization: Bearer ..."
  ROBO_PORTA    padrêo 8765
  ROBO_VOZ      voz do espeak-ng quando o servidor nêo manda áudio (padrêo pt-br; ex.: en-us, es)
  ROBO_SEM_AUDIO=1  nêo usa microfone nem alto-falante (testes)

Contrato do servidor (JSON): {"audio_wav_b64": "...", "texto": "...", "sessao": "robo-mesa"}
  → {"ouvido": "o que entendeu", "resposta": "texto", "audio_wav_b64": "opcional"}
Sem "audio_wav_b64" na resposta, o robô fala o texto com o espeak-ng.
"""
import array, base64, json, os, queue, shutil, struct, subprocess, tempfile, threading, time, wave
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROSTO = AQUI.parent / 'rosto' / 'index.html'
JARVIS_URL = os.environ.get('JARVIS_URL', '').rstrip('/')
JARVIS_TOKEN = os.environ.get('JARVIS_TOKEN', '')
SEM_AUDIO = os.environ.get('ROBO_SEM_AUDIO') == '1'
VOZ = os.environ.get('ROBO_VOZ', 'pt-br')
MAX_GRAVACAO = 12  # segundos


class Robo:
    def __init__(self):
        self.estado = 'ocioso'
        self.ouvintes = []
        self.trava = threading.Lock()
        self.arecord = None
        self.arquivo = None
        self.ocupado = False

    # --- rosto ---
    def emitir(self, **d):
        for q in list(self.ouvintes):
            q.put(d)

    def mudar(self, estado):
        self.estado = estado
        self.emitir(estado=estado, nivel=0)

    # --- gravaçêo ---
    def ouvir(self):
        with self.trava:
            if self.ocupado:
                return False
            self.ocupado = True
        self.mudar('ouvindo')
        self.arquivo = Path(tempfile.mkstemp(suffix='.wav')[1])
        if not SEM_AUDIO:
            self.arecord = subprocess.Popen(['arecord', '-q', '-f', 'S16_LE', '-r', '16000', '-c', '1',
                                             '-d', str(MAX_GRAVACAO), str(self.arquivo)])
            threading.Timer(MAX_GRAVACAO + 0.5, self.parar).start()
        return True

    def parar(self, wav_pronto=None):
        if self.estado != 'ouvindo':
            return False
        if self.arecord:
            self.arecord.terminate(); self.arecord.wait(); self.arecord = None
        threading.Thread(target=self.conversar, args=(wav_pronto,), daemon=True).start()
        return True

    # --- conversa ---
    def conversar(self, wav_pronto=None, texto=None):
        try:
            self.mudar('pensando')
            wav = wav_pronto if wav_pronto is not None else (self.arquivo.read_bytes() if self.arquivo and self.arquivo.exists() else b'')
            resp = self.perguntar(wav, texto)
            self.falar(resp)
        except Exception as e:                      # o robô nunca trava: mostra e volta
            print('erro na conversa:', repr(e), flush=True)
            self.mudar('dormindo'); time.sleep(2)
        finally:
            if self.arquivo and self.arquivo.exists():
                self.arquivo.unlink()
            self.mudar('ocioso')
            self.ocupado = False

    def perguntar(self, wav, texto):
        if not JARVIS_URL:
            raise RuntimeError('defina JARVIS_URL')
        corpo = {'sessao': 'robo-mesa'}
        if wav:
            corpo['audio_wav_b64'] = base64.b64encode(wav).decode()
        if texto:
            corpo['texto'] = texto
        req = urllib.request.Request(JARVIS_URL + '/conversa', json.dumps(corpo).encode(),
                                     {'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + JARVIS_TOKEN} if JARVIS_TOKEN else {})})
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)

    def falar(self, resp):
        wav = base64.b64decode(resp['audio_wav_b64']) if resp.get('audio_wav_b64') else None
        if wav is None and resp.get('resposta') and not SEM_AUDIO and shutil.which('espeak-ng'):
            tmp = tempfile.mkstemp(suffix='.wav')[1]
            subprocess.run(['espeak-ng', '-v', VOZ, '-w', tmp, resp['resposta']], check=True)
            wav = Path(tmp).read_bytes(); Path(tmp).unlink()
        if wav is None:
            self.mudar('feliz'); time.sleep(1.5); return
        self.mudar('falando')
        niveis = envelope(wav)
        proc = None
        if not SEM_AUDIO:
            tmp = tempfile.mkstemp(suffix='.wav')[1]; Path(tmp).write_bytes(wav)
            proc = subprocess.Popen(['aplay', '-q', tmp])
        t0 = time.time()
        for i, n in enumerate(niveis):             # só o áudio da RESPOSTA mexe na boca
            time.sleep(max(0, t0 + i * 0.05 - time.time()))
            self.emitir(nivel=n)
        if proc:
            proc.wait()
        self.mudar('feliz'); time.sleep(1.2)


def envelope(wav_bytes, passo=0.05):
    """Nível 0..1 do áudio da resposta a cada 50 ms (só biblioteca padrêo)."""
    import io
    with wave.open(io.BytesIO(wav_bytes)) as w:
        n, canais, largura = w.getframerate(), w.getnchannels(), w.getsampwidth()
        dados = w.readframes(w.getnframes())
    if largura != 2:
        return [0.5] * int(len(dados) / max(1, n * canais * largura) / passo)
    a = array.array('h'); a.frombytes(dados)
    bloco = max(1, int(n * canais * passo))
    saida = []
    for i in range(0, len(a), bloco):
        parte = a[i:i + bloco]
        rms = (sum(x * x for x in parte) / max(1, len(parte))) ** 0.5
        saida.append(min(1.0, rms / 9000))
    return saida


ROBO = Robo()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, d, c=200):
        b = json.dumps(d).encode(); self.send_response(c); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path == '/':
            b = ROSTO.read_bytes(); self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
        elif self.path == '/estado':
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            q = queue.Queue(); ROBO.ouvintes.append(q); q.put({'estado': ROBO.estado})
            try:
                while True:
                    try:
                        d = q.get(timeout=15); self.wfile.write(b'data: ' + json.dumps(d).encode() + b'\n\n')
                    except queue.Empty:
                        self.wfile.write(b': vivo\n\n')
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                ROBO.ouvintes.remove(q)
        elif self.path == '/saude':
            self._json({'estado': ROBO.estado, 'jarvis': bool(JARVIS_URL)})
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); corpo = self.rfile.read(n) if n else b''
        if self.path == '/ouvir':
            self._json({'ok': ROBO.ouvir()})
        elif self.path == '/parar':
            self._json({'ok': ROBO.parar()})
        elif self.path == '/texto':                      # teste sem microfone: {"texto": "..."}
            t = json.loads(corpo or b'{}').get('texto', '')
            if ROBO.ocupado:
                self._json({'ok': False}); return
            ROBO.ocupado = True; ROBO.estado = 'ouvindo'
            threading.Thread(target=ROBO.conversar, kwargs={'wav_pronto': b'', 'texto': t}, daemon=True).start()
            self._json({'ok': True})
        else:
            self.send_error(404)


def main():
    porta = int(os.environ.get('ROBO_PORTA', '8765'))
    print(f'Robô conversa em http://127.0.0.1:{porta}/  (Jarvis: {JARVIS_URL or "NêO configurado"})', flush=True)
    ThreadingHTTPServer(('127.0.0.1', porta), H).serve_forever()


if __name__ == '__main__':
    main()
