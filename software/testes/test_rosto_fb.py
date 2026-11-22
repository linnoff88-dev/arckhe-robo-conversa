import json, os, struct, sys, tempfile, threading, time, unittest, urllib.request
from pathlib import Path
from http.server import HTTPServer, ThreadingHTTPServer

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'rosto')); sys.path.insert(0, str(AQUI.parent / 'ponte'))
os.environ['ROBO_SEM_AUDIO'] = '1'
os.environ['JARVIS_URL'] = 'http://127.0.0.1:18788'
import jarvis_falso, robo, rosto_fb   # noqa: E402


class T(unittest.TestCase):
    def test_todos_os_estados_desenham_e_diferem(self):
        vistos = {}
        for e in ['dormindo', 'ocioso', 'ouvindo', 'pensando', 'falando', 'feliz']:
            r = rosto_fb.Rosto(320, 240); r.estado = e; r.nivel = r.nivel_alvo = 0.7
            im = r.quadro(t=0.5, aleatorio=False)
            self.assertEqual(im.size, (320, 240))
            self.assertIn(rosto_fb.AMARELO, set(im.getdata()))     # tem amarelo INEMA no rosto
            vistos[e] = im.tobytes()
        self.assertEqual(len(set(vistos.values())), 6)             # cada estado tem desenho próprio

    def test_boca_abre_com_o_nivel_da_resposta(self):
        r = rosto_fb.Rosto(); r.estado = 'falando'
        r.nivel = r.nivel_alvo = 0.0; a = sum(1 for p in r.quadro(t=0.5, aleatorio=False).getdata() if p == rosto_fb.AMARELO)
        r.nivel = r.nivel_alvo = 1.0; b = sum(1 for p in r.quadro(t=0.5, aleatorio=False).getdata() if p == rosto_fb.AMARELO)
        self.assertGreater(b, a)

    def test_tela_maior_escala(self):
        self.assertEqual(rosto_fb.Rosto(480, 320).quadro(t=0.5, aleatorio=False).size, (480, 320))

    def test_rgb565(self):
        from PIL import Image
        for rgb, esperado in [((255, 0, 0), 0xF800), ((0, 255, 0), 0x07E0), ((0, 0, 255), 0x001F), ((0, 0, 0), 0)]:
            self.assertEqual(struct.unpack('<H', rosto_fb.rgb565(Image.new('RGB', (1, 1), rgb)))[0], esperado)
        self.assertEqual(len(rosto_fb.rgb565(Image.new('RGB', (320, 240)))), 320 * 240 * 2)

    def test_toque_vira_acao(self):
        n = struct.calcsize(rosto_fb.FORMATO_EVENTO)
        ev = lambda tipo, cod, val: struct.pack(rosto_fb.FORMATO_EVENTO, 0, 0, tipo, cod, val)
        arq = tempfile.mkstemp()[1]
        Path(arq).write_bytes(ev(3, 0, 120) + ev(1, 0x14A, 1) + ev(1, 0x14A, 0) + ev(1, 0x14A, 1))   # coordenada, toque, solta, toque
        cont = []
        rosto_fb.ler_toques(arq, lambda: cont.append(1), threading.Event())
        os.unlink(arq)
        self.assertEqual(len(cont), 2)

    def test_estado_da_ponte_real_chega_ao_rosto(self):
        j = HTTPServer(('127.0.0.1', 18788), jarvis_falso.H); threading.Thread(target=j.serve_forever, daemon=True).start()
        p = ThreadingHTTPServer(("127.0.0.1", 18766), robo.H); threading.Thread(target=p.serve_forever, daemon=True).start()
        rosto_fb.URL = 'http://127.0.0.1:18766'
        r = rosto_fb.Rosto(); parar = threading.Event()
        threading.Thread(target=rosto_fb.ouvir_estado, args=(r, parar), daemon=True).start()
        time.sleep(0.6)
        rq = urllib.request.Request('http://127.0.0.1:18766/texto', json.dumps({'texto': 'oi'}).encode(), {'Content-Type': 'application/json'}, method='POST')
        self.assertTrue(json.load(urllib.request.urlopen(rq, timeout=5))['ok'])
        vistos, fim = set(), time.time() + 8
        while time.time() < fim and 'falando' not in vistos:
            vistos.add(r.estado); time.sleep(0.05)
        parar.set(); j.shutdown(); p.shutdown()
        self.assertIn('falando', vistos)

    def test_previa_png(self):
        out = tempfile.mkstemp(suffix='.png')[1]
        sys.argv = ['rosto_fb.py', '--png', 'falando', out]; rosto_fb.main()
        self.assertGreater(Path(out).stat().st_size, 500); os.unlink(out)


if __name__ == '__main__':
    unittest.main(verbosity=2)
