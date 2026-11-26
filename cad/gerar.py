#!/usr/bin/env python3
"""Robô conversa: suporte de mesa para o Raspberry Pi 3 com tela de 7" (estudo mecânico 01).

Executar: ../robos-impressos/.venv/bin/python cad/gerar.py   (grava estudo/)

Quadro do DISPLAY (antes de inclinar): X lateral, Y para trás (frente da tela em y=0),
Z para cima. O conjunto é entêo inclinado INCL graus para trás e levantado ALTURA mm.
Quadro do MUNDO: a base apoia em z=0. Unidade: mm.

Dimensões das fontes (conferir com paquímetro nas suas peças antes de imprimir):
- Tela oficial Raspberry Pi 7" (800x480): contorno 192,96 x 110,76 mm, área visível 155 x 86 mm.
  https://www.raspberrypi.com/documentation/accessories/display.html
- Raspberry Pi 3 B: placa 85 x 56 mm, furos M2,5 em 58 x 49 mm, USB/Ethernet no lado curto.
"""
from pathlib import Path
import json
import numpy as np
import trimesh
from manifold3d import Manifold, OpType, CrossSection, FillRule, JoinType
from PIL import Image, ImageDraw, ImageFont
from skimage.measure import find_contours

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'estudo'
OUT.mkdir(exist_ok=True)

# ---------------- parâmetros (mude aqui se a sua tela for outra) ----------------
TELA_W, TELA_H, TELA_E = 194.0, 111.0, 7.0      # contorno da tela (com folga) e espessura sem a placa
JANELA_W, JANELA_H = 158.0, 90.0                # abertura da moldura sobre a área visível (155 x 86)
FOLGA = 0.4                                     # folga lateral por lado
BORDA_X = 10.0                                  # moldura além da tela, por lado
CHIN = 30.0                                     # queixo abaixo da tela (INEMA + pescoço)
TOPO = 10.0
W = TELA_W + 2 * BORDA_X                        # 214
H = CHIN + TELA_H + TOPO                        # 151
ZC = CHIN + TELA_H / 2                          # centro da tela
MOLDURA_E = 6.0                                 # espessura da moldura (frente em y = -6)
PISO_E = 5.0                                    # fundo da placa atrás da tela
Y_PISO = TELA_E + 0.4                           # frente do piso
Y_TRAS = Y_PISO + PISO_E                        # costas da placa (y = 12,4)
JAN_PI_W, JAN_PI_H = 104.0, 72.0                # vêo atrás da tela para a placa do driver
BOLSO_W, BOLSO_H, BOLSO_D = 100.0, 72.0, 44.0   # bolso interno da caixa do Pi
PAREDE = 3.0
PEDRA_Y = 10.0                                  # a placa do driver ocupa os primeiros 10 mm do bolso
CAIXA_MAX = (98.0, 68.0, 30.5)                  # maior caixa de Pi que cabe (x, z, y)
INCL = 12.0                                     # inclinaçêo para trás
ALTURA = 62.0                                   # altura da borda inferior da placa
BASE_X, BASE_Y0, BASE_Y1, BASE_E = 105.0, -48.0, 92.0, 8.0

M3_FURO, M3_PILOTO, M25_PILOTO = 3.4, 2.6, 2.2

# ---------------- áudio PREVISTO (microfone + alto-falante) ----------------
# Microfone MEMS em placa pequena (ex.: INMP441, 14 x 14 mm, ~3 mm de espessura com solda): bolso no topo da
# moldura/placa, deitado, com UM furo de som para cima (longe do alto-falante) e canal de fio até o vêo do Pi.
MIC_PLACA = (14.0, 14.0, 3.2)                   # x, y, z da placa do microfone (conferir a sua com paquímetro)
MIC_BOLSO_X, MIC_Y0, MIC_Y1 = 15.0, -4.5, 10.5  # bolso: 15 mm de largura, y de -4,5 a 10,5 (quadro do display)
MIC_Z0, MIC_Z1 = H - 8.5, H - 3.5               # bolso 5 mm de altura; 3,5 mm de pele no topo
MIC_PORTA_Y, MIC_PORTA_D = 3.0, 2.4             # furo de som no topo
# Alto-falante redondo de 40 mm (3 W, ~20 mm de profundidade) numa caixa ao lado do pescoço, soando para cima.
SPK_D, SPK_E = 40.0, 20.0                       # diâmetro e profundidade do alto-falante (conferir o seu)
POD_X0, POD_X1, POD_Y0, POD_Y1, POD_H = -98.0, -46.0, -22.0, 28.0, 31.0
POD_PAREDE, POD_TOPO = 3.0, 3.0


def slab(x0, x1, z0, z1, y0, y1, r=0.0):
    """Placa no plano XZ, de y0 a y1, com cantos de raio r (visto de frente)."""
    w, h = x1 - x0, z1 - z0
    if r > 0:
        cs = CrossSection.square([w - 2 * r, h - 2 * r]).translate([x0 + r, -z1 + r])
        cs = cs.offset(r, JoinType.Round, 2, 48)
    else:
        cs = CrossSection.square([w, h]).translate([x0, -z1])
    return cs.extrude(y1 - y0).rotate([-90, 0, 0]).translate([0, y0, 0])


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def union(parts):
    return Manifold.batch_boolean(parts, OpType.Add)


def furo(x, z, y0, comp, d=M3_FURO):
    """Cilindro ao longo de +Y a partir de y0."""
    return Manifold.cylinder(comp, d / 2, d / 2, 32).rotate([-90, 0, 0]).translate([x, y0, z])


def poste(x, z, y0, comp, d):
    return furo(x, z, y0, comp, d)


def mesh(solid):
    m = solid.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=True)


def mundo(solid):
    """Quadro do display → mundo: inclina INCL para trás em torno da origem e levanta ALTURA."""
    return solid.rotate([-INCL, 0, 0]).translate([0, 0, ALTURA])


def texto(largura, texto_='INEMA'):
    """Contorno do texto em (x, a) com a = -z (para slab-like); engrossado 0,2 mm por lado."""
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 200)
    b = font.getbbox(texto_)
    mask = Image.new('L', (b[2] - b[0] + 20, b[3] - b[1] + 20), 0)
    ImageDraw.Draw(mask).text((10 - b[0], 10 - b[1]), texto_, font=font, fill=255)
    cont = find_contours(np.asarray(mask), 127.5)
    paths = [np.column_stack([c[:, 1], c[:, 0]]) for c in cont]      # (coluna, linha): linha cresce para baixo = a
    xy = np.vstack(paths)
    esc = largura / (xy[:, 0].max() - xy[:, 0].min())
    mid = (xy.min(axis=0) + xy.max(axis=0)) / 2
    paths = [(p - mid) * esc for p in paths]
    return CrossSection(paths, FillRule.EvenOdd).simplify(0.03).offset(0.2, JoinType.Round, 2, 24).simplify(0.01)


# ---------------- peças no quadro do display ----------------
X_PAR_LAT = (W / 2) - BORDA_X / 2                 # x dos parafusos da moldura nas laterais
PAR_MOLDURA = [(sx * X_PAR_LAT, z) for sx in (-1, 1) for z in (50.0, 121.0)] + \
              [(sx * 75.0, 15.0) for sx in (-1, 1)]
PAR_PESCOCO = [(sx * 30.0, z) for sx in (-1, 1) for z in (8.0, 22.0)]
FL_X, FL_Z = 61.0, 47.0                           # meia largura/altura do flange da caixa
PAR_CAIXA = [(sx * 57.0, ZC + sz * 43.0) for sx in (-1, 1) for sz in (-1, 1)]
JAN_Z_TOPO = ZC + JAN_PI_H / 2                    # topo do vêo do driver (onde o canal do microfone começa)


def moldura():
    s = slab(-W / 2, W / 2, 0, H, -MOLDURA_E, 0, 9)
    s -= slab(-JANELA_W / 2, JANELA_W / 2, ZC - JANELA_H / 2, ZC + JANELA_H / 2, -MOLDURA_E - 1, 1, 4)
    for x, z in PAR_MOLDURA:
        s -= furo(x, z, -MOLDURA_E + 1.8, 4.2 + 0.1, M3_PILOTO)   # piloto cego, 1,8 mm de pele na frente
    s -= box(-MIC_BOLSO_X / 2, MIC_BOLSO_X / 2, MIC_Y0, 0.5, MIC_Z0, MIC_Z1)               # bolso do microfone (metade da frente)
    relevo = texto(60.0).extrude(1.35).rotate([-90, 0, 0]).translate([0, -MOLDURA_E - 1.2, 0])
    relevo = relevo.translate([0, 0, CHIN / 2 - 0.0])
    # texto centrado no queixo: o contorno está centrado em (0,0) com a = -z
    return s + relevo


def placa():
    s = slab(-W / 2, W / 2, 0, H, 0, Y_TRAS, 9)
    s -= slab(-(TELA_W + 2 * FOLGA) / 2, (TELA_W + 2 * FOLGA) / 2, CHIN - FOLGA, CHIN + TELA_H + FOLGA, -1, Y_PISO, 2)
    s -= slab(-JAN_PI_W / 2, JAN_PI_W / 2, ZC - JAN_PI_H / 2, ZC + JAN_PI_H / 2, Y_PISO - 1, Y_TRAS + 1, 3)
    for x, z in PAR_MOLDURA:
        s -= furo(x, z, -1, Y_TRAS + 2, M3_FURO)
    for x, z in PAR_CAIXA:
        s -= furo(x, z, Y_TRAS - 4.0, 4.1, M3_PILOTO)
    for x, z in PAR_PESCOCO:
        s -= furo(x, z, Y_TRAS - 9.0, 9.1, M3_PILOTO)
    s -= box(-MIC_BOLSO_X / 2, MIC_BOLSO_X / 2, -0.5, MIC_Y1, MIC_Z0, MIC_Z1)               # bolso do microfone (metade de trás)
    s -= Manifold.cylinder(6.0, MIC_PORTA_D / 2, MIC_PORTA_D / 2, 24).translate([0, MIC_PORTA_Y, MIC_Z1 - 0.5])   # furo de som, para cima
    s -= box(-3, 3, 8.6, 11.4, JAN_Z_TOPO - 0.5, MIC_Z0 + 0.5)                              # canal interno do fio até o vêo do Pi
    return s


def caixa():
    y0, y1 = Y_TRAS, Y_TRAS + BOLSO_D
    ext_x, ext_z = BOLSO_W / 2 + PAREDE, BOLSO_H / 2 + PAREDE
    corpo = slab(-ext_x, ext_x, ZC - ext_z, ZC + ext_z, y0, y1, 4)
    corpo -= slab(-BOLSO_W / 2, BOLSO_W / 2, ZC - BOLSO_H / 2, ZC + BOLSO_H / 2, y0 - 1, y1 + 1, 2)
    partes = [corpo, slab(-FL_X, FL_X, ZC - FL_Z, ZC + FL_Z, y0, y0 + 3, 6)]
    for x, z in PAR_CAIXA:                                    # orelhas do parafuso da tampa (bloco no canto)
        sx, sz = np.sign(x), np.sign(z - ZC)
        xa, xb = sorted([sx * (ext_x - 5), sx * (FL_X)])
        za, zb = sorted([ZC + sz * (ext_z - 5), ZC + sz * FL_Z])
        partes.append(box(xa, xb, y1 - 16, y1, za, zb))
    # apoios nos cantos (a caixa ou o adaptador assentam aqui)
    ay = Y_TRAS + PEDRA_Y + 3.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            cx, cz = sx * (BOLSO_W / 2 - 4.6), ZC + sz * (BOLSO_H / 2 - 4.6)
            partes.append(box(cx - 4, cx + 4, ay - 6, ay, cz - 4, cz + 4))
    s = union(partes)
    s -= slab(-BOLSO_W / 2, BOLSO_W / 2, ZC - BOLSO_H / 2, ZC + BOLSO_H / 2, y0 - 1, y1 + 1, 2)
    # o flange nêo pode tapar o vêo para a placa do driver
    # saída de USB/Ethernet: lateral direita; cabos e portas: parede de baixo
    s -= box(BOLSO_W / 2 - 1, ext_x + 1, y0 + PEDRA_Y + 4, y1 + 1, ZC - 31, ZC + 31)
    s -= box(-48, 36, y0 + 6, y1 + 1, ZC - ext_z - 1, ZC - BOLSO_H / 2 + 1)
    for x, z in PAR_CAIXA:
        s -= furo(x, z, y0 - 1, 4.5, M3_FURO)               # parafusos para a placa
        s -= furo(x, z, y1 - 9, 9.1, M3_PILOTO)             # piloto da tampa
    for sx in (-1, 1):
        for sz in (-1, 1):
            cx, cz = sx * (BOLSO_W / 2 - 4.6), ZC + sz * (BOLSO_H / 2 - 4.6)
            s -= furo(cx, cz, ay - 5, 5.1, M3_PILOTO)
    return s


def tampa():
    y0 = Y_TRAS + BOLSO_D
    s = slab(-FL_X, FL_X, ZC - FL_Z, ZC + FL_Z, y0, y0 + 3, 6)
    for x, z in PAR_CAIXA:
        s -= furo(x, z, y0 - 1, 5, M3_FURO)
    for i in range(-5, 6):                                    # ventilaçêo do Pi
        s -= slab(i * 9 - 2, i * 9 + 2, ZC - 28, ZC + 28, y0 - 1, y0 + 4, 2)
    return s


def adaptador():
    """Para o Pi SEM caixa: placa com 4 postes M2,5 (58 x 49 mm). USB/Ethernet para a direita."""
    ay = Y_TRAS + PEDRA_Y + 3.0
    s = slab(-BOLSO_W / 2 + 0.6, BOLSO_W / 2 - 0.6, ZC - BOLSO_H / 2 + 0.6, ZC + BOLSO_H / 2 - 0.6, ay, ay + 3, 4)
    s -= slab(-46, 42, ZC - 20, ZC + 20, ay - 1, ay + 4, 4)       # alivia peso e deixa passar o cabo
    px = -6.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            s += poste(px + sx * 29, ZC + sz * 24.5, ay + 2.9, 5.1, 6.0)
    # (o rebaixo acima atravessa a placa: reforço em barras nas linhas dos postes)
    for sz in (-1, 1):
        s += box(px - 33, px + 33, ay, ay + 3, ZC + sz * 24.5 - 4, ZC + sz * 24.5 + 4)
    for sx in (-1, 1):
        s += box(px + sx * 29 - 4, px + sx * 29 + 4, ay, ay + 3, ZC - 28.5, ZC + 28.5)
    for sx in (-1, 1):
        for sz in (-1, 1):
            cx, cz = sx * (BOLSO_W / 2 - 4.6), ZC + sz * (BOLSO_H / 2 - 4.6)
            s += box(cx - 4, cx + 4, ay, ay + 3, cz - 4, cz + 4)
    for sx in (-1, 1):
        for sz in (-1, 1):
            cx, cz = sx * (BOLSO_W / 2 - 4.6), ZC + sz * (BOLSO_H / 2 - 4.6)
            s -= furo(cx, cz, ay - 1, 5, M3_FURO)
    for sx in (-1, 1):
        for sz in (-1, 1):
            s -= furo(px + sx * 29, ZC + sz * 24.5, ay + 3.0, 5.2, M25_PILOTO)
    return s


POD_Z0 = BASE_E
POD_Z1 = BASE_E + POD_H
POD_CX, POD_CY = (POD_X0 + POD_X1) / 2, (POD_Y0 + POD_Y1) / 2
POD_PARAFUSOS = [(POD_X0 + 5, POD_Y0 + 5), (POD_X1 - 5, POD_Y1 - 5)]
SPK_TOPO = POD_Z1 - POD_TOPO - 3.0              # o alto-falante encosta no anel de apoio


def modulo_som():
    """Caixa do alto-falante, no MUNDO, ao lado esquerdo do pescoço, aberta embaixo (fecha na base).
    Imprime de cabeça para baixo (a pele do topo na mesa). Alto-falante entra por baixo e encosta num anel."""
    s = box(POD_X0, POD_X1, POD_Y0, POD_Y1, POD_Z0, POD_Z1)
    s -= box(POD_X0 + POD_PAREDE, POD_X1 - POD_PAREDE, POD_Y0 + POD_PAREDE, POD_Y1 - POD_PAREDE, POD_Z0 - 1, POD_Z1 - POD_TOPO)
    anel = Manifold.cylinder(3.0, 24.0, 24.0, 64) - Manifold.cylinder(3.0, 18.0, 18.0, 64)
    s += anel.translate([POD_CX, POD_CY, POD_Z1 - POD_TOPO - 3.0])
    for x, y in POD_PARAFUSOS:                                           # colunas dos parafusos
        s += Manifold.cylinder(POD_Z1 - POD_TOPO - POD_Z0 + 0.5, 4.2, 4.2, 32).translate([x, y, POD_Z0])
        s -= Manifold.cylinder(10.0, 1.3, 1.3, 24).translate([x, y, POD_Z0 - 1])
    pontos = [(0.0, 0.0)] + [(8 * np.cos(a), 8 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 6, endpoint=False)] \
             + [(14 * np.cos(a + 0.26), 14 * np.sin(a + 0.26)) for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)]
    for dx, dy in pontos:                                                # grade de som no topo
        s -= Manifold.cylinder(POD_TOPO + 2, 1.5, 1.5, 16).translate([POD_CX + dx, POD_CY + dy, POD_Z1 - POD_TOPO - 1])
    s -= box(POD_X1 - POD_PAREDE - 1, POD_X1 + 1, 10, 18, POD_Z0 + 2, POD_Z0 + 8)   # saída do cabo do alto-falante
    return s


def pescoco_e_base():
    """Peça única, no MUNDO: base com furos de mesa + pescoço oco inclinado."""
    cs = CrossSection.square([2 * BASE_X - 32, BASE_Y1 - BASE_Y0 - 32]).translate([-BASE_X + 16, BASE_Y0 + 16])
    cs = cs.offset(16, JoinType.Round, 2, 64)
    base = cs.extrude(BASE_E)
    # pescoço no quadro do display
    zb = -70.0
    ext = box(-40, 40, Y_TRAS, Y_TRAS + 34, zb, 28)
    ext -= box(-36.5, 36.5, Y_TRAS + 3.5, Y_TRAS + 34 - 3.5, zb - 1, 29)
    for x, z in PAR_PESCOCO:                                   # passagem dos 4 parafusos M3 pela parede da frente
        ext -= furo(x, z, Y_TRAS - 0.5, 4.5, M3_FURO)
    # abertura de cabos na parede traseira, perto da base (cota no mundo: z 9..23)
    pesc = mundo(ext)
    pesc ^= box(-200, 200, -200, 200, 4, 400)                        # corta o que passaria da base
    s = base + pesc
    s -= box(-13, 13, 30, 70, 9, 23)          # boca de saída dos cabos na parede de trás
    s -= box(-41.5, -35.5, 8, 30, BASE_E, 15)   # janela do lado esquerdo: o cabo do alto-falante entra no pescoço
    for x, y in POD_PARAFUSOS:                  # parafusos M3 de baixo para cima, que prendem a caixa do alto-falante
        s -= Manifold.cylinder(BASE_E + 2, 1.7, 1.7, 24).translate([x, y, -1])
        s -= Manifold.cylinder(3.0, 4.8, 1.7, 24).translate([x, y, -0.01])
    # parafusos de mesa (escareados) nos 4 cantos
    for sx in (-1, 1):
        for y in (BASE_Y0 + 16, BASE_Y1 - 16):
            s -= Manifold.cylinder(BASE_E + 2, 2.3, 2.3, 24).translate([sx * 87, y, -1])
            s -= Manifold.cylinder(3.0, 2.3, 4.8, 24).translate([sx * 87, y, BASE_E - 3.0])
    # INEMA em relevo na frente da base
    # o contorno vem com a = linha para baixo; no plano XY da base y cresce para trás → inverter
    rel = texto(70.0).mirror([0, 1]).extrude(1.35).translate([0, BASE_Y0 + 24, BASE_E - 0.15])
    return s + rel


# ---------------- montagem e verificaçêo ----------------
def principal():
    P = {'moldura': moldura(), 'placa': placa(), 'caixa': caixa(), 'tampa': tampa(), 'adaptador': adaptador()}
    P['pescoco_base'] = None
    return P


MUNDO = ('pescoco_base', 'modulo_som')               # peças já desenhadas no quadro do mundo


def mundo_partes(P):
    return {k: (mundo(v) if k not in MUNDO else v) for k, v in P.items()}


def rot(angulo, eixo=(1, 0, 0)):
    return trimesh.transformations.rotation_matrix(np.radians(angulo), eixo)


# orientaçêo de impressêo: ângulo em torno de X aplicado ao quadro do display
IMPRESSAO = {'moldura': -90, 'placa': -90, 'caixa': 90, 'tampa': 90, 'adaptador': 90, 'pescoco_base': 0, 'modulo_som': 180}
NOME = {'moldura': 'moldura', 'placa': 'placa-traseira', 'caixa': 'bolso-do-pi', 'tampa': 'tampa',
        'adaptador': 'adaptador-pi-sem-caixa', 'pescoco_base': 'base-e-pescoco', 'modulo_som': 'caixa-do-alto-falante'}


def verificar():
    P = principal()
    P['pescoco_base'] = pescoco_e_base()
    P['modulo_som'] = modulo_som()
    rel = {'status': 'estudo; nêo liberado para impressêo final', 'pecas': {}, 'checagens': {},
           'parametros': {'tela_mm': [TELA_W, TELA_H], 'janela_mm': [JANELA_W, JANELA_H], 'inclinacao_graus': INCL,
                          'altura_borda_inferior_mm': ALTURA, 'bolso_caixa_mm': [BOLSO_W, BOLSO_H, BOLSO_D],
                          'caixa_maxima_mm': list(CAIXA_MAX),
                          'microfone_placa_mm': list(MIC_PLACA), 'alto_falante_mm': [SPK_D, SPK_E]}}
    impr = {}
    for k, v in P.items():
        m = mesh(v)
        m.apply_transform(rot(IMPRESSAO[k]))
        m.apply_translation(-m.bounds[0])
        m.export(OUT / f'{NOME[k]}-ESTUDO.stl')
        dims = m.extents
        # área de apoio: faces voltadas para baixo coladas na mesa
        n = m.face_normals
        baixo = (n[:, 2] < -0.99) & (m.triangles[:, :, 2].max(axis=1) < 0.05)
        apoio = float(m.area_faces[baixo].sum())
        ok = bool(m.is_watertight and m.is_volume and len(m.split()) == 1 and np.all(dims <= 256))
        rel['pecas'][NOME[k]] = {'malha_fechada': bool(m.is_watertight), 'volume_positivo': bool(m.is_volume),
                                 'corpos': len(m.split()), 'dimensoes_impressao_mm': dims.round(1).tolist(),
                                 'volume_cm3': round(m.volume / 1000, 1), 'area_apoio_mesa_mm2': round(apoio),
                                 'geometria_basica_ok': ok}
        assert ok, (k, m.is_watertight, m.is_volume, len(m.split()), dims)
        assert apoio > 1500, (k, apoio)           # lado de apoio realmente colado na mesa
        impr[k] = m
    W_ = mundo_partes(P)
    # envelopes (quadro do display)
    tela = box(-TELA_W / 2, TELA_W / 2, 0, TELA_E, CHIN, CHIN + TELA_H)
    driver = box(-47, 47, TELA_E, Y_TRAS + PEDRA_Y, ZC - 31, ZC + 31)
    y_ap = Y_TRAS + PEDRA_Y + 3.0
    caixa_pi = box(-CAIXA_MAX[0] / 2, CAIXA_MAX[0] / 2, y_ap, y_ap + CAIXA_MAX[2], ZC - CAIXA_MAX[1] / 2, ZC + CAIXA_MAX[1] / 2)
    pi_nu = box(-6 - 32.5 - 0.0, -6 - 32.5 + 85, y_ap + 3 + 5, y_ap + 3 + 5 + 1.6 + 16.5, ZC - 28, ZC + 28)
    pi_nu_placa = box(-6 - 32.5, -6 - 32.5 + 85, y_ap + 3 + 5, y_ap + 3 + 5 + 1.6, ZC - 28, ZC + 28)
    conj = ['moldura', 'placa', 'caixa', 'tampa']
    tol = 0.01
    pares = [(a, b) for i, a in enumerate(conj) for b in conj[i + 1:]]
    rel['checagens']['interferencia_pares_mm3'] = {}
    for a, b in pares:
        v = (P[a] ^ P[b]).volume()
        rel['checagens']['interferencia_pares_mm3'][f'{a}×{b}'] = round(v, 4)
        assert v < tol, (a, b, v)
    for nm, env, quem in [('tela', tela, ['moldura', 'caixa', 'tampa']), ('placa_do_driver', driver, ['moldura', 'placa', 'caixa', 'tampa']),
                          ('caixa_pi_maxima', caixa_pi, ['moldura', 'placa', 'caixa', 'tampa'])]:
        for q in quem:
            v = (P[q] ^ env).volume()
            rel['checagens'][f'interferencia_{nm}_{q}_mm3'] = round(v, 4)
            assert v < tol, (nm, q, v)
    # tela precisa estar APOIADA no piso e coberta pela moldura (contato de borda, sem sobreposiçêo)
    # Pi sem caixa: adaptador + placa do Pi + componentes
    for q in ['caixa', 'tampa', 'placa', 'moldura']:
        v = (P[q] ^ pi_nu).volume()
        rel['checagens'][f'interferencia_pi_sem_caixa_{q}_mm3'] = round(v, 4)
        assert v < tol, ('pi nu', q, v)
    for q in ['caixa', 'tampa', 'placa', 'moldura']:
        v = (P['adaptador'] ^ P[q]).volume()
        rel['checagens'][f'interferencia_adaptador_{q}_mm3'] = round(v, 4)
        assert v < tol, ('adaptador', q, v)
    v = (P['adaptador'] ^ pi_nu_placa).volume()
    rel['checagens']['interferencia_pi_sem_caixa_adaptador_mm3'] = round(v, 4)
    assert v < tol, ('pi nu adaptador', v)
    # pescoço/base × display (mundo)
    for q in ['moldura', 'placa', 'caixa', 'tampa']:
        v = (W_[q] ^ P['pescoco_base']).volume()
        rel['checagens'][f'interferencia_{q}_pescoco_mm3'] = round(v, 4)
        assert v < tol, (q, 'pescoço', v)
    # teste negativo: caixa de Pi grande demais tem que colidir
    grande = box(-CAIXA_MAX[0] / 2 - 1.5, CAIXA_MAX[0] / 2 + 1.5, y_ap, y_ap + CAIXA_MAX[2], ZC - CAIXA_MAX[1] / 2, ZC + CAIXA_MAX[1] / 2)
    neg = (P['caixa'] ^ grande).volume()
    assert neg > 1, neg
    rel['checagens']['negativo_caixa_larga_mm3'] = round(neg, 1)
    grossa = box(-CAIXA_MAX[0] / 2, CAIXA_MAX[0] / 2, y_ap, y_ap + CAIXA_MAX[2] + 3, ZC - CAIXA_MAX[1] / 2, ZC + CAIXA_MAX[1] / 2)
    neg2 = (P['tampa'] ^ grossa).volume()
    assert neg2 > 1, neg2
    rel['checagens']['negativo_caixa_grossa_mm3'] = round(neg2, 1)
    # retirada do Pi (caixa) pelas costas, sem tirar a tampa de lugar: tampa removida → corredor livre
    for dy in (5, 20, 60):
        mov = caixa_pi.translate([0, dy, 0])
        assert (P['caixa'] ^ mov).volume() < tol and (P['placa'] ^ mov).volume() < tol
    rel['checagens']['retirada_da_caixa_pelas_costas'] = 'passou (3 posições) para o envelope retangular, tampa removida'
    for x, z in PAR_PESCOCO:
        fura = furo(x, z, Y_TRAS - 0.2, 3.0, 2.8)
        assert (P['pescoco_base'].__class__ is Manifold) and (mundo(fura) ^ P['pescoco_base']).volume() < tol, ('parafuso do pescoço bate na parede', x, z)
    rel['checagens']['parafusos_do_pescoco_passam_pela_parede'] = 'passou (4 posições, cilindro de 2,8 mm livre)'
    # contato do pescoço com o queixo da placa: a face da frente do pescoço tem que pegar na placa
    toque = box(-40, 40, Y_TRAS - 0.2, Y_TRAS, 0, 28)
    contato = (P['placa'] ^ toque).volume()
    rel['checagens']['contato_pescoco_queixo_mm3'] = round(contato, 1)
    assert contato > 0.8 * 80 * 28 * 0.2 * 0.8, contato
    # cabos: um cilindro de 12 mm desce do vêo de baixo da caixa até a saída do pescoço
    cabo = Manifold.cylinder(ZC - 30 + 35, 6, 6, 32).translate([0, Y_TRAS + 17, -35])
    for q in ['moldura', 'placa', 'caixa', 'tampa']:
        assert (P[q] ^ cabo).volume() < tol, ('cabo', q)
    assert (mundo(cabo) ^ P['pescoco_base']).volume() < tol, 'cabo × pescoço'
    rel['checagens']['corredor_de_cabos_12mm'] = 'livre: vêo da caixa → boca do pescoço (sem colisêo com nenhuma peça)'
    saida = box(-13, 13, 40, 60, 9, 23)
    moldura_saida = box(-16, 16, 40, 60, 6, 26)
    livre = (saida ^ P['pescoco_base']).volume()
    parede = (moldura_saida ^ P['pescoco_base']).volume()
    assert livre < tol and parede > 100, (livre, parede)
    rel['checagens']['saida_de_cabos_atras'] = f'aberta (0 mm³ dentro do vêo) e cercada pela parede ({parede:.0f} mm³ ao redor)'
    # ---- áudio: microfone ----
    mic = box(-MIC_PLACA[0] / 2, MIC_PLACA[0] / 2, MIC_Y0 + 0.5, MIC_Y0 + 0.5 + MIC_PLACA[1], MIC_Z0 + 0.7, MIC_Z0 + 0.7 + MIC_PLACA[2])
    porta = Manifold.cylinder(MIC_Z1 + 3 - (MIC_Z0 + 0.7 + MIC_PLACA[2]), MIC_PORTA_D / 2 - 0.05, MIC_PORTA_D / 2 - 0.05, 24)\
        .translate([0, MIC_PORTA_Y, MIC_Z0 + 0.7 + MIC_PLACA[2]])
    fio = box(-2, 2, 9, 10.4, JAN_Z_TOPO, MIC_Z0 + 0.4)      # fio de 4 x 1,4 mm: do vêo do Pi ao bolso, dentro do canal
    for q in ['moldura', 'placa', 'caixa', 'tampa']:
        for nm, env in [('placa_do_microfone', mic), ('caminho_do_som', porta), ('fio_do_microfone', fio)]:
            v = (P[q] ^ env).volume()
            rel['checagens'][f'interferencia_{nm}_{q}_mm3'] = round(v, 4)
            assert v < tol, (nm, q, v)
    grande_mic = box(-8.25, 8.25, MIC_Y0 + 0.5, MIC_Y0 + 0.5 + MIC_PLACA[1], MIC_Z0 + 0.7, MIC_Z0 + 0.7 + MIC_PLACA[2])
    neg_mic = (P['moldura'] ^ grande_mic).volume() + (P['placa'] ^ grande_mic).volume()
    assert neg_mic > 1, neg_mic
    rel['checagens']['negativo_microfone_largo_mm3'] = round(neg_mic, 1)
    # ---- áudio: alto-falante (no mundo) ----
    spk = Manifold.cylinder(SPK_E, SPK_D / 2, SPK_D / 2, 64).translate([POD_CX, POD_CY, SPK_TOPO - SPK_E])
    spk_grande = Manifold.cylinder(SPK_E, 24.0, 24.0, 64).translate([POD_CX, POD_CY, SPK_TOPO - SPK_E])
    pod = P['modulo_som']
    v = (pod ^ spk).volume()
    rel['checagens']['interferencia_alto_falante_caixa_mm3'] = round(v, 4)
    assert v < tol, ('alto-falante × caixa', v)
    neg_spk = (pod ^ spk_grande).volume()
    assert neg_spk > 1, neg_spk
    rel['checagens']['negativo_alto_falante_grande_mm3'] = round(neg_spk, 1)
    for q in ['moldura', 'placa', 'caixa', 'tampa']:
        v = (W_[q] ^ pod).volume()
        rel['checagens'][f'interferencia_{q}_caixa_do_alto_falante_mm3'] = round(v, 4)
        assert v < tol, (q, 'caixa do alto-falante', v)
    v = (pod ^ P['pescoco_base']).volume()
    rel['checagens']['interferencia_caixa_do_alto_falante_base_mm3'] = round(v, 4)
    assert v < tol, ('caixa do alto-falante × base', v)
    cabo_som = box(POD_X1 - 4, -35, 11, 17, POD_Z0 + 2.5, 15)
    assert (pod ^ cabo_som).volume() < tol and (P['pescoco_base'] ^ cabo_som).volume() < tol, 'cabo do alto-falante'
    rel['checagens']['cabo_do_alto_falante_ate_o_pescoco'] = 'livre: saída da caixa → janela do pescoço → vêo interno'
    # o furo de som do topo da caixa precisa estar aberto (cilindro vertical livre sobre o centro)
    grade = Manifold.cylinder(POD_TOPO + 1.0, 1.4, 1.4, 16).translate([POD_CX, POD_CY, POD_Z1 - POD_TOPO - 0.5])
    assert (pod ^ grade).volume() < tol, 'grade fechada'
    rel['checagens']['grade_de_som_aberta'] = 'passou (furo central livre)'
    # estabilidade: centro de massa (PLA 1,24 g/cm3 a ~35% efetivo; tela 300 g; Pi 80 g)
    mass, cg = 0.0, np.zeros(3)
    for k in ['moldura', 'placa', 'caixa', 'tampa']:
        m = mesh(W_[k]); g = m.volume / 1000 * 1.24 * 0.35
        mass += g; cg += g * m.center_mass
    mb = mesh(P['pescoco_base']); g = mb.volume / 1000 * 1.24 * 0.35
    mass += g; cg += g * mb.center_mass
    mp = mesh(pod); gp = mp.volume / 1000 * 1.24 * 0.35
    mass += gp; cg += gp * mp.center_mass
    for g, env in [(300.0, mundo(tela)), (80.0, mundo(caixa_pi)), (40.0, spk)]:
        e = mesh(env); mass += g; cg += g * e.center_mass
    cg /= mass
    altura_topo = float(mesh(W_['moldura']).bounds[1][2])
    margem_tras = BASE_Y1 - cg[1]; margem_frente = cg[1] - BASE_Y0
    tomba_tras = mass / 1000 * 9.81 * (margem_tras / 1000) / (altura_topo / 1000)
    rel['checagens']['estabilidade'] = {'massa_estimada_g': round(mass), 'centro_de_massa_mm': cg.round(1).tolist(),
                                        'margem_ate_a_borda_traseira_mm': round(margem_tras, 1),
                                        'margem_ate_a_borda_dianteira_mm': round(margem_frente, 1),
                                        'forca_no_topo_que_tomba_para_tras_N_sem_parafusos': round(tomba_tras, 1),
                                        'altura_do_topo_mm': round(altura_topo, 1)}
    assert abs(cg[0]) < 12, cg           # a caixa só de um lado nêo pode tirar o robô do eixo
    assert margem_frente > 30 and margem_tras > 30
    rel['limites'] = [
        'Sem fatiamento nem teste físico: os STL sêo de ESTUDO.',
        'Contorno da tela, posiçêo da área visível, furos e conectores vêm da folha de dados; conferir com paquímetro.',
        'A tela oficial de 7" (800x480) é a de referência. A Touch Display 2 tem outro contorno (189,5 x 120 mm): mudar os parâmetros.',
        'A placa do driver da tela e os parafusos reais nêo foram modelados; foi reservado um vêo de 104 x 72 x 10 mm.',
        'O espaço para a caixa do Pi é um limite (98 x 68 x 30,5 mm), nêo o desenho de uma caixa específica.',
        'Estabilidade estimada com massas aproximadas; sem os parafusos na mesa um toque firme pode tombar o robô.',
        'Microfone e alto-falante sêo PREVISTOS no desenho (bolso, furo de som, canal de fio e caixa ao lado do pescoço); nenhum foi ligado nem testado com som real.',
        'Placa do microfone (14 x 14 x 3,2 mm) e alto-falante (40 mm, 20 mm de profundidade) sêo medidas típicas: conferir as suas peças com paquímetro.',
        'Microfone perto do alto-falante pode captar a própria voz: o software pausa a escuta enquanto fala, mas só o teste real prova.',
        'Sem análise de resistência dos pilotos de parafuso nem de aquecimento do Pi dentro do bolso.']
    (OUT / 'verificacao.json').write_text(json.dumps(rel, ensure_ascii=False, indent=2) + '\n')
    return P, W_, rel, impr, dict(tela=tela, driver=driver, caixa_pi=caixa_pi)


COR = {'moldura': [24, 24, 30, 255], 'placa': [70, 80, 91, 255], 'caixa': [70, 80, 91, 255], 'tampa': [215, 166, 55, 255],
       'adaptador': [90, 160, 110, 255], 'pescoco_base': [215, 166, 55, 255], 'modulo_som': [90, 160, 110, 255], 'tela': [20, 20, 24, 255],
       'caixa_pi': [236, 235, 228, 160], 'driver': [30, 120, 80, 255]}

if __name__ == '__main__':
    P, W_, rel, impr, env = verificar()
    scene = trimesh.Scene()
    objs = {k: mesh(v) for k, v in W_.items() if k != 'adaptador'}
    objs['tela'] = mesh(mundo(env['tela']))
    objs['caixa_pi'] = mesh(mundo(env['caixa_pi']))
    for k, m in objs.items():
        m.visual.face_colors = COR[k]
        scene.add_geometry(m, node_name=k)
    scene.export(OUT / 'montagem-ESTUDO.glb')
    # peças na posiçêo de montagem (mundo) para o render
    pasta = OUT / 'partes-mundo'
    pasta.mkdir(exist_ok=True)
    for k, v in W_.items():
        mesh(v).export(pasta / f'{k}.stl')
    mesh(mundo(env['tela'])).export(pasta / 'tela.stl')
    mesh(mundo(env['caixa_pi'])).export(pasta / 'caixa_pi.stl')
    mesh(mundo(env['driver'])).export(pasta / 'driver.stl')
    # Pi sem caixa (representaçêo simples: placa + bloco USB/Ethernet) para o render
    y_ap = Y_TRAS + PEDRA_Y + 3.0
    pi_placa = box(-38.5, 46.5, y_ap + 8, y_ap + 9.6, ZC - 28, ZC + 28)
    pi_usb = box(26.5, 46.5, y_ap + 9.6, y_ap + 26, ZC - 24, ZC + 17)
    mesh(mundo(union([pi_placa, pi_usb]))).export(pasta / 'pi_nu.stl')
    # vista explodida: afasta as peças ao longo do eixo Y do display
    ex = OUT / 'partes-explodida'
    ex.mkdir(exist_ok=True)
    for k, off in [('moldura', -45), ('placa', 0), ('caixa', 40), ('tampa', 110), ('adaptador', 75)]:
        mesh(mundo(P[k].translate([0, off, 0]))).export(ex / f'{k}.stl')
    mesh(mundo(env['tela'].translate([0, -22, 0]))).export(ex / 'tela.stl')
    mesh(mundo(union([pi_placa, pi_usb]).translate([0, 75, 0]))).export(ex / 'pi_nu.stl')
    mesh(P['pescoco_base']).export(ex / 'pescoco_base.stl')
    mesh(P['modulo_som'].translate([-30, 0, 25])).export(ex / 'modulo_som.stl')
    print(json.dumps(rel, ensure_ascii=False, indent=2))
