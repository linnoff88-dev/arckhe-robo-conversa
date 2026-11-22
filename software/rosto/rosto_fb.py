#!/usr/bin/env python3
"""Rosto do robô para telas pequenas por GPIO (2,4" 320x240, 3,5" 480x320): desenha direto no framebuffer.

Sem navegador. Precisa só de Pillow e numpy (no Pi: sudo apt install python3-pil python3-numpy).
Fala com a ponte (ponte/robo.py) pelos mesmos pontos do rosto de navegador: lê /estado (SSE) e manda /ouvir e /parar.

  ROSTO_URL    padrão http://127.0.0.1:8765
  ROSTO_FB     framebuffer da tela (padrão /dev/fb1; confira com `ls /dev/fb*`)
  ROSTO_LARG / ROSTO_ALT   tamanho da tela (padrão 320 x 240)
  ROSTO_TOQUE  dispositivo do toque, ex. /dev/input/event0 (confira com `ls /dev/input/by-path`); sem ele, sem toque
  ROSTO_GIRO   0, 90, 180 ou 270 (padrão 0): gira o desenho se a tela estiver montada de lado

Prévia sem tela:  python3 rosto_fb.py --png falando /tmp/rosto.png
"""
import json, math, os, random, struct, sys, threading, time, urllib.request
from PIL import Image, ImageDraw

URL = os.environ.get('ROSTO_URL', 'http://127.0.0.1:8765').rstrip('/')
FB = os.environ.get('ROSTO_FB', '/dev/fb1')
LARG, ALT = int(os.environ.get('ROSTO_LARG', '320')), int(os.environ.get('ROSTO_ALT', '240'))
TOQUE = os.environ.get('ROSTO_TOQUE', '')
GIRO = int(os.environ.get('ROSTO_GIRO', '0'))
AMARELO, FUNDO, AZUL, CINZA = (250, 204, 21), (12, 12, 16), (56, 189, 248), (107, 114, 128)


class Rosto:
    """Mesmo desenho do rosto de navegador, em escala para a tela pequena."""

    def __init__(self, larg=LARG, alt=ALT):
        self.w, self.h = larg, alt
        self.estado, self.nivel, self.nivel_alvo = 'ocioso', 0.0, 0.0
        self.piscar, self.prox_piscar = 0.0, 2.0
        self.olha = [0.0, 0.0]; self.alvo = [0.0, 0.0]
        self.t0 = time.time()

    def quadro(self, t=None, aleatorio=True):
        t = (time.time() - self.t0) if t is None else t
        w, h = self.w, self.h
        k = w / 320.0                                    # escala em relação ao desenho base de 320 x 240
        im = Image.new('RGB', (w, h), FUNDO)
        d = ImageDraw.Draw(im)
        if t > self.prox_piscar:
            self.piscar = 1.0; self.prox_piscar = t + 2 + (random.random() * 3.5 if aleatorio else 2.0)
        self.piscar = max(0.0, self.piscar - 0.12)
        fechado = 1.0 if self.estado == 'dormindo' else (math.sin(self.piscar * math.pi) if self.piscar > 0 else 0.0)
        if self.estado == 'pensando':
            self.alvo = [-24 * k, -16 * k]
        elif self.estado in ('ouvindo', 'falando'):
            self.alvo = [0.0, 0.0]
        elif aleatorio and random.random() < 0.01:
            self.alvo = [(random.random() - .5) * 36 * k, (random.random() - .5) * 16 * k]
        for i in (0, 1):
            self.olha[i] += (self.alvo[i] - self.olha[i]) * 0.1
        self.nivel += (self.nivel_alvo - self.nivel) * 0.45
        grande = 1.12 if self.estado == 'ouvindo' else 1.0
        ew, eh = 66 * k * grande, 84 * k * grande * (1 - 0.93 * fechado)
        eh = max(eh * (0.55 if self.estado == 'feliz' else 1.0), 5 * k)
        cx, cy = (96 * k, 225 * k), 88 * k
        for x in cx:
            x0, y0 = x + self.olha[0] - ew / 2, cy + self.olha[1] - eh / 2
            d.rounded_rectangle([x0, y0, x0 + ew, y0 + eh], radius=min(18 * k, eh / 2), fill=AMARELO)
            if self.estado == 'feliz':                   # sorriso: apaga a metade de baixo dos olhos
                d.rectangle([x0 - 2, cy + self.olha[1] + eh * 0.1, x0 + ew + 2, y0 + eh + 2], fill=FUNDO)
        if self.estado == 'falando':                     # boca abre com o NÍVEL DA RESPOSTA (o microfone não mexe nela)
            bh = 5 * k + self.nivel * 34 * k
            d.rounded_rectangle([160 * k - 38 * k, 178 * k - bh / 2, 160 * k + 38 * k, 178 * k + bh / 2], radius=6 * k, fill=AMARELO)
        elif self.estado == 'feliz':
            d.arc([160 * k - 30 * k, 150 * k, 160 * k + 30 * k, 205 * k], 20, 160, fill=AMARELO, width=max(4, int(6 * k)))
        else:
            d.rounded_rectangle([160 * k - 24 * k, 178 * k - 2.5 * k, 160 * k + 24 * k, 178 * k + 2.5 * k], radius=3 * k, fill=AMARELO)
        if self.estado == 'ouvindo':                     # moldura azul que pulsa
            a = 0.5 + 0.4 * math.sin(t * 6)
            cor = tuple(int(f + (c - f) * a) for f, c in zip(FUNDO, AZUL))
            d.rounded_rectangle([3, 3, w - 4, h - 4], radius=int(12 * k), outline=cor, width=max(2, int(3 * k)))
        if self.estado == 'pensando':
            for i in range(3):
                a = 0.3 + 0.7 * max(0.0, math.sin(t * 5 - i))
                cor = tuple(int(f + (c - f) * a) for f, c in zip(FUNDO, AMARELO))
                x, y, r = (144 + i * 16) * k, 214 * k, 4 * k
                d.ellipse([x - r, y - r, x + r, y + r], fill=cor)
        if self.estado == 'dormindo':
            d.text((236 * k, 28 * k), 'z z z', fill=CINZA)
        return im.rotate(GIRO, expand=True) if GIRO else im


def rgb565(im):
    """Imagem RGB do Pillow → bytes RGB565 little-endian (o que o framebuffer de tela SPI espera)."""
    import numpy as np
    a = np.asarray(im.convert('RGB'), dtype=np.uint16)
    v = ((a[:, :, 0] & 0xF8) << 8) | ((a[:, :, 1] & 0xFC) << 3) | (a[:, :, 2] >> 3)
    return v.astype('<u2').tobytes()


def ouvir_estado(rosto, parar):
    """Lê o fluxo /estado da ponte e atualiza o rosto; reconecta sozinho."""
    while not parar.is_set():
        try:
            with urllib.request.urlopen(URL + '/estado', timeout=30) as r:
                for linha in r:
                    if parar.is_set():
                        return
                    linha = linha.decode('utf-8', 'replace').strip()
                    if linha.startswith('data:'):
                        d = json.loads(linha[5:])
                        if d.get('estado'):
                            rosto.estado = d['estado']
                        if 'nivel' in d:
                            rosto.nivel_alvo = d['nivel']
        except Exception:
            time.sleep(1.5)


BTN_TOUCH, EV_KEY = 0x14A, 0x01
FORMATO_EVENTO = 'llHHi'                      # struct input_event do Linux (struct timeval + tipo + código + valor)


def ler_toques(caminho, acao, parar):
    """Chama acao() a cada toque (dedo encostando). Lê o evento cru do Linux; sem biblioteca extra."""
    n = struct.calcsize(FORMATO_EVENTO)
    try:
        with open(caminho, 'rb', buffering=0) as f:
            while not parar.is_set():
                dado = f.read(n)
                if len(dado) < n:
                    return
                _, _, tipo, codigo, valor = struct.unpack(FORMATO_EVENTO, dado)
                if tipo == EV_KEY and codigo == BTN_TOUCH and valor == 1:
                    acao()
    except OSError as e:
        print('toque indisponível:', e, flush=True)


class Gravador:
    """Toque começa a ouvir; outro toque termina e manda ao Jarvis (igual ao rosto de navegador)."""

    def __init__(self, rosto):
        self.rosto, self.gravando = rosto, False

    def alternar(self):
        try:
            rq = urllib.request.Request(URL + ('/parar' if self.gravando else '/ouvir'), b'', method='POST')
            urllib.request.urlopen(rq, timeout=5).read()
            self.gravando = not self.gravando
        except Exception as e:
            print('ponte fora do ar:', e, flush=True)

    def sincronizar(self):
        if self.rosto.estado != 'ouvindo':
            self.gravando = False


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--png':          # prévia sem tela
        r = Rosto(); r.estado = sys.argv[2]; r.nivel_alvo = r.nivel = 0.6
        r.quadro(t=0.5, aleatorio=False).save(sys.argv[3] if len(sys.argv) > 3 else 'rosto.png')
        return
    r = Rosto(); parar = threading.Event(); g = Gravador(r)
    threading.Thread(target=ouvir_estado, args=(r, parar), daemon=True).start()
    if TOQUE:
        threading.Thread(target=ler_toques, args=(TOQUE, g.alternar, parar), daemon=True).start()
    print(f'Rosto no framebuffer {FB} ({LARG}x{ALT}), ponte {URL}, toque {TOQUE or "desligado"}', flush=True)
    with open(FB, 'wb', buffering=0) as fb:
        while True:
            t = time.time()
            fb.seek(0); fb.write(rgb565(r.quadro())); g.sincronizar()
            time.sleep(max(0, 1 / 15 - (time.time() - t)))


if __name__ == '__main__':
    main()
