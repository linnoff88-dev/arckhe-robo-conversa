import json, os, subprocess, sys, threading, time, unittest, urllib.request
from pathlib import Path
from http.server import HTTPServer

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'ponte'))
os.environ['ROBO_SEM_AUDIO'] = '1'
os.environ['JARVIS_URL'] = 'http://127.0.0.1:18787'
os.environ['JARVIS_TOKEN'] = 'segredo-de-teste'
import jarvis_falso, robo   # noqa: E402


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.j = HTTPServer(('127.0.0.1', 18787), jarvis_falso.H); threading.Thread(target=cls.j.serve_forever, daemon=True).start()
        cls.r = HTTPServer(('127.0.0.1', 18765), robo.H); threading.Thread(target=cls.r.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.j.shutdown(); cls.r.shutdown()

    def post(self, rota, corpo=b''):
        rq = urllib.request.Request(f'http://127.0.0.1:18765{rota}', corpo, {'Content-Type': 'application/json'}, method='POST')
        return json.load(urllib.request.urlopen(rq, timeout=5))

    def test_pagina_do_rosto_e_saude(self):
        h = urllib.request.urlopen('http://127.0.0.1:18765/', timeout=5).read().decode()
        self.assertIn('EventSource', h); self.assertIn('Toque', h)
        self.assertTrue(json.load(urllib.request.urlopen('http://127.0.0.1:18765/saude'))['jarvis'])

    def test_conversa_completa_estados_e_token(self):
        q = __import__('queue').Queue(); robo.ROBO.ouvintes.append(q)
        self.assertTrue(self.post('/texto', json.dumps({'texto': 'oi'}).encode())['ok'])
        estados, niveis = [], []
        fim = time.time() + 8
        while time.time() < fim:
            try: d = q.get(timeout=0.5)
            except Exception: continue
            if 'estado' in d: estados.append(d['estado'])
            if d.get('nivel'): niveis.append(d['nivel'])
            if estados[-1:] == ['ocioso'] and 'falando' in estados: break
        robo.ROBO.ouvintes.remove(q)
        for e in ('pensando', 'falando', 'feliz', 'ocioso'):
            self.assertIn(e, estados)
        self.assertTrue(estados.index('pensando') < estados.index('falando') < estados.index('ocioso'))
        self.assertTrue(max(niveis) > 0.05, 'a boca deve abrir com o áudio da resposta')
        v = jarvis_falso.H.visto[-1]
        self.assertEqual(v['texto'], 'oi'); self.assertEqual(v['auth'], 'Bearer segredo-de-teste')

    def test_envelope_so_do_audio(self):
        e = robo.envelope(jarvis_falso.tom(1.0))
        self.assertTrue(18 <= len(e) <= 21); self.assertTrue(max(e) > 0.3)
        silencio = robo.envelope(jarvis_falso.tom(0.5, 1) )
        self.assertTrue(len(silencio) > 5)

    def test_erro_do_servidor_nao_trava(self):
        antes = robo.JARVIS_URL; robo.JARVIS_URL = 'http://127.0.0.1:1'
        try:
            robo.ROBO.ocupado = False
            self.assertTrue(self.post('/texto', json.dumps({'texto': 'x'}).encode())['ok'])
            time.sleep(3.5)
            self.assertFalse(robo.ROBO.ocupado); self.assertEqual(robo.ROBO.estado, 'ocioso')
        finally:
            robo.JARVIS_URL = antes


if __name__ == '__main__':
    unittest.main(verbosity=2)
