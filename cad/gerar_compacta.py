#!/usr/bin/env python3
"""Robô conversa COMPACTO: Raspberry Pi 3 sem caixa + tela de 2,4" encaixada no GPIO + microfone USB (estudo mecânico 02).

Executar: ../robos-impressos/.venv/bin/python cad/gerar_compacta.py   (grava estudo/compacta/)

Ideia: a tela de 2,4" é uma placa que se encaixa no conector de 40 pinos do Pi (como um HAT), então o Pi fica
logo ATRÁS da tela. A cabeça é uma caixa de duas peças (frente com janela + tampa com 4 postes M2,5 que seguram
o Pi) apoiada num poste oco sobre uma base. O som sai da própria placa da tela (alto-falante integrado); o
microfone USB espeta numa porta USB do Pi, que fica numa janela da lateral direita.

Quadro da CABEÇA: x lateral (0 = centro da janela da tela), y para trás (frente da cabeça em y = 0), z para cima
(0 = centro da janela). Unidade: mm. Quadro do MUNDO: a base apoia em z = 0.

TODAS as medidas da tela abaixo são TÍPICAS de placa 2,4" no formato Pi Zero (65 x 56,5 mm); o anúncio não traz o
contorno. MEÇA a sua com o paquímetro e mude só os números em "parâmetros" (os testes dizem se ainda cabe):
- Raspberry Pi 3 B: placa 85 x 56 mm, furos M2,5 em 58 x 49 mm, altura total ~17 mm, USB/Ethernet no lado curto direito.
  https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-mechanical-drawing.pdf
"""
from pathlib import Path
import json
import numpy as np
import trimesh
from manifold3d import Manifold, OpType

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'estudo' / 'compacta'
OUT.mkdir(parents=True, exist_ok=True)

# ---------------- parâmetros (mude aqui conforme as suas peças) ----------------
PI_W, PI_H, PI_PCB, PI_ALT = 85.0, 56.0, 1.6, 17.0   # placa do Pi, espessura da placa, altura total
PI_FUROS = (58.0, 49.0)                              # espaçamento dos furos M2,5 (x, z)
HAT_W, HAT_H, HAT_E = 65.0, 56.5, 7.0                # placa da tela 2,4": contorno e espessura com o LCD
HAT_DX = 0.0                                         # deslocamento do Pi em relação à borda esquerda da tela
JAN_W, JAN_H = 52.0, 40.0                            # janela da frente (área visível ~49 x 36,7, centrada)
EMPILHA = 9.0                                        # vão entre a placa da tela e a placa do Pi (altura do conector)
FOLGA = 0.6
PAREDE, FRENTE_E, TAMPA_E = 3.0, 3.0, 3.0
SOBRA_TRAS = 6.5                                     # espaço atrás da placa do Pi (cartão SD, solda)
M3_FURO, M3_PILOTO, M25_PILOTO = 3.4, 2.6, 2.2
BASE_X, BASE_Y0, BASE_Y1, BASE_E = 65.0, -35.0, 70.0, 7.0
POSTE_X, POSTE_Y0, POSTE_Y1, POSTE_ALT, POSTE_P = 56.0, -2.0, 32.0, 62.0, 3.0

# derivadas
PI_X0 = -HAT_W / 2 + HAT_DX                          # borda esquerda do Pi
PI_X1 = PI_X0 + PI_W
Y_PI = FRENTE_E + HAT_E + EMPILHA                    # face da frente da placa do Pi
Y_FIM = Y_PI + PI_PCB + SOBRA_TRAS                   # fim da cavidade (frente da tampa)
INT_X = max(abs(PI_X0), abs(PI_X1)) + FOLGA          # meia largura interna (cabeça simétrica em volta da janela)
INT_Z = max(HAT_H, PI_H) / 2 + FOLGA
EXT_X, EXT_Z = INT_X + PAREDE, INT_Z + PAREDE
Y_TRAS = Y_FIM + TAMPA_E


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cil_y(x, z, y0, comp, d):
    return Manifold.cylinder(comp, d / 2, d / 2, 32).rotate([-90, 0, 0]).translate([x, y0, z])


def cil_z(x, y, z0, comp, d):
    return Manifold.cylinder(comp, d / 2, d / 2, 32).translate([x, y, z0])


def union(p):
    return Manifold.batch_boolean(p, OpType.Add)


def mesh(s):
    m = s.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=True)


# parafusos que fecham a tampa na caixa (4 cantos) e furos do Pi
PAR_TAMPA = [(sx * (EXT_X - 4.0), sz * (EXT_Z - 4.0)) for sx in (-1, 1) for sz in (-1, 1)]
PI_PARAF = [(PI_X0 + 3.5 + sx, PI_H / 2 * 0 + sz) for sx in (0, PI_FUROS[0]) for sz in (-PI_FUROS[1] / 2, PI_FUROS[1] / 2)]
PAR_POSTE = [(-46.0, 9.0), (-46.0, 20.0)]            # parafusos M3 poste → cabeça (lado esquerdo, longe do Pi)
CABO = (-36.0, -2.0)                                 # x do vão de cabos no fundo da cabeça (alimentação do Pi)


def frente():
    s = box(-EXT_X, EXT_X, 0, Y_FIM, -EXT_Z, EXT_Z)
    s -= box(-INT_X, INT_X, FRENTE_E, Y_FIM + 1, -INT_Z, INT_Z)                       # cavidade
    s -= box(-JAN_W / 2, JAN_W / 2, -1, FRENTE_E + 1, -JAN_H / 2, JAN_H / 2)            # janela da tela
    # colunas dos parafusos da tampa nos cantos
    y_col = Y_PI + PI_PCB + 3.0                                                        # só ATRÁS da placa do Pi (não bate no canto dela)
    for x, z in PAR_TAMPA:
        s += box(x - 3.5, x + 3.5, y_col, Y_FIM, z - 3.5, z + 3.5)
        s -= cil_y(x, z, Y_FIM - 7.0, 7.1, M3_PILOTO)
    # janela da lateral direita: USB e Ethernet do Pi (o microfone USB espeta aqui)
    s -= box(INT_X - 1, EXT_X + 1, Y_PI - 15.0, Y_PI + PI_PCB + 1, -PI_H / 2 - 1, PI_H / 2 + 1)
    # vão do fundo: alimentação (micro USB) e HDMI/P2 do Pi; o cabo desce pelo poste
    s -= box(CABO[0] - 14, CABO[0] + 36, Y_PI - 12, Y_FIM + 1, -EXT_Z - 1, -INT_Z + 1)
    # bosses do poste (no chão da cabeça, lado esquerdo, fora da área do Pi)
    for x, y in PAR_POSTE:
        s += box(x - 4.5, x + 4.5, y - 4.5, y + 4.5, -INT_Z - 0.5, -INT_Z + 7.0)
        s -= cil_z(x, y, -EXT_Z - 1, 14.0, M3_PILOTO)
    return s


def tampa():
    s = box(-EXT_X, EXT_X, Y_FIM, Y_TRAS, -EXT_Z, EXT_Z)
    for x, z in PAR_TAMPA:
        s -= cil_y(x, z, Y_FIM - 1, TAMPA_E + 2, M3_FURO)
    for x, z in PI_PARAF:                                                                # 4 postes do Pi, apontando para a frente
        s += cil_y(x, z, Y_PI + PI_PCB, Y_FIM - (Y_PI + PI_PCB) + 0.01, 5.0)
        s -= cil_y(x, z, Y_PI + PI_PCB - 0.5, Y_FIM - Y_PI - PI_PCB + 0.5 + 0.0, M25_PILOTO)
    for i in range(-4, 5):                                                               # ventilação
        s -= box(i * 9 - 2, i * 9 + 2, Y_FIM - 1, Y_TRAS + 1, -20, 20)
    return s


def poste_e_base():
    s = box(-BASE_X, BASE_X, BASE_Y0, BASE_Y1, 0, BASE_E)
    topo = BASE_E + POSTE_ALT
    p = box(-POSTE_X, POSTE_X, POSTE_Y0, POSTE_Y1, BASE_E, topo)
    # oco: o cabo de força sobe por dentro e sai pelo vão da cabeça; janela atrás, perto da base
    p -= box(-POSTE_X + POSTE_P, POSTE_X - POSTE_P, POSTE_Y0 + POSTE_P, POSTE_Y1 - POSTE_P, BASE_E - 1, topo - POSTE_P)
    p -= box(CABO[0] - 6, CABO[0] + 26, POSTE_Y0 + 6, POSTE_Y1 - 6, topo - POSTE_P - 1, topo + 1)       # abertura de cima
    p -= box(-10, 14, POSTE_Y1 - POSTE_P - 1, POSTE_Y1 + 1, BASE_E + 4, BASE_E + 18)                    # saída de cabos atrás
    s += p
    for x, y in PAR_POSTE:                                                                # parafusos M3 do topo do poste
        s -= cil_z(x, y, topo - POSTE_P - 1, POSTE_P + 2, M3_FURO)
    for sx in (-1, 1):                                                                    # parafusos de mesa
        for y in (BASE_Y0 + 14, BASE_Y1 - 14):
            s -= cil_z(sx * (BASE_X - 14), y, -1, BASE_E + 2, M3_FURO)
    return s


def mundo_cabeca(s):
    """Cabeça → mundo: janela centrada em x = 0; o fundo da cabeça apoia no topo do poste."""
    return s.translate([0, 0, BASE_E + POSTE_ALT + EXT_Z])


def verificar():
    P = {'frente': frente(), 'tampa': tampa(), 'poste_base': poste_e_base()}
    tol = 0.01
    rel = {'status': 'estudo 02 (compacto); medidas da tela são típicas e NÃO confirmadas', 'pecas': {}, 'checagens': {},
           'parametros': {'tela_placa_mm': [HAT_W, HAT_H, HAT_E], 'janela_mm': [JAN_W, JAN_H], 'pi_mm': [PI_W, PI_H, PI_ALT],
                          'cabeca_externa_mm': [round(2 * EXT_X, 1), round(2 * EXT_Z, 1), round(Y_TRAS, 1)]}}
    imp = {'frente': (90, 'cabeca-frente'), 'tampa': (-90, 'cabeca-tampa'), 'poste_base': (0, 'poste-e-base')}
    for k, v in P.items():
        m = mesh(v)
        ang, nome = imp[k]
        if ang:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), (1, 0, 0)))
        m.apply_translation(-m.bounds[0])
        m.export(OUT / f'{nome}-ESTUDO.stl')
        n = m.face_normals
        apoio = float(m.area_faces[(n[:, 2] < -0.99) & (m.triangles[:, :, 2].max(axis=1) < 0.05)].sum())
        ok = bool(m.is_watertight and m.is_volume and len(m.split()) == 1 and np.all(m.extents <= 256))
        rel['pecas'][nome] = {'malha_fechada': bool(m.is_watertight), 'corpos': len(m.split()),
                              'dimensoes_impressao_mm': m.extents.round(1).tolist(), 'volume_cm3': round(m.volume / 1000, 1),
                              'area_apoio_mesa_mm2': round(apoio), 'geometria_basica_ok': ok}
        assert ok, (k, m.is_watertight, len(m.split()), m.extents)
        assert apoio > 1000, (k, apoio)
    # envelopes
    tela = box(PI_X0, PI_X0 + HAT_W, FRENTE_E, FRENTE_E + HAT_E, -HAT_H / 2, HAT_H / 2)
    pi_placa = box(PI_X0, PI_X1, Y_PI, Y_PI + PI_PCB, -PI_H / 2, PI_H / 2)
    pi_comp = box(PI_X1 - 20, PI_X1, Y_PI - 13.5, Y_PI, -PI_H / 2, PI_H / 2)              # USB e Ethernet (lado direito)
    pi_sd = box(PI_X0 - 2.5, PI_X0 + 12, Y_PI + PI_PCB, Y_PI + PI_PCB + 2.5, -6, 6)       # cartão microSD, que sobra 2,5 mm da borda
    pi_solda = box(PI_X0 + 12, PI_X1 - 12, Y_PI + PI_PCB, Y_PI + PI_PCB + 2.0, -PI_H / 2 + 12, PI_H / 2 - 12)   # pontas de solda
    for nm, env in [('tela', tela), ('pi_placa', pi_placa), ('pi_usb_ethernet', pi_comp), ('pi_cartao_sd', pi_sd), ('pi_solda', pi_solda)]:
        for q in ['frente', 'tampa']:
            v = (P[q] ^ env).volume()
            rel['checagens'][f'interferencia_{nm}_{q}_mm3'] = round(v, 4)
            assert v < tol, (nm, q, v)
    v = (P['frente'] ^ P['tampa']).volume()
    assert v < tol, ('frente × tampa', v)
    # a tela tem que ser VISTA: janela menor que a placa e dentro da área da tela
    assert JAN_W < HAT_W and JAN_H < HAT_H
    rel['checagens']['janela_dentro_da_placa'] = f'{JAN_W} x {JAN_H} dentro de {HAT_W} x {HAT_H}'
    # janela USB: um plugue USB-A (14 x 7 mm) entra na lateral até a porta do Pi
    plugue = box(PI_X1 - 15, EXT_X + 25, Y_PI - 12, Y_PI - 5, -20, -6)
    assert (P['frente'] ^ plugue).volume() < tol, 'plugue USB bate na caixa'
    rel['checagens']['plugue_usb_entra_pela_lateral'] = 'livre (14 x 7 mm, 3 posições de porta cobertas pela janela)'
    # cabo de força: desce do vão da cabeça pelo poste
    cabo = box(CABO[0] - 4, CABO[0] + 4, 8.0, 15.0, -EXT_Z - 3, -INT_Z + 12)
    assert (P['frente'] ^ cabo).volume() < tol and (P['tampa'] ^ cabo).volume() < tol, 'cabo × cabeça'
    cab_m = mundo_cabeca(cabo)
    assert (cab_m ^ P['poste_base']).volume() < tol, 'cabo × poste'
    rel['checagens']['cabo_de_forca_cabeca_poste'] = 'livre (8 x 8 mm da cavidade até dentro do poste)'
    # a cabeça apoia no poste e não o atravessa
    f_m, t_m = mundo_cabeca(P['frente']), mundo_cabeca(P['tampa'])
    for nm, v in [('frente', f_m), ('tampa', t_m)]:
        c = (v ^ P['poste_base']).volume()
        rel['checagens'][f'interferencia_{nm}_poste_mm3'] = round(c, 4)
        assert c < tol, (nm, c)
    toque = box(-EXT_X, EXT_X, 0, Y_TRAS, BASE_E + POSTE_ALT - 0.05, BASE_E + POSTE_ALT + 0.0)
    assert (mundo_cabeca(P['frente']).translate([0, 0, -0.04]) ^ P['poste_base']).volume() > 50, 'cabeça não apoia no poste'
    rel['checagens']['cabeca_apoia_no_poste'] = 'sim (contato por cima do poste)'
    # parafusos poste → cabeça: o cilindro de 2,8 mm passa livre pelo topo do poste e entra no boss da frente
    for x, y in PAR_POSTE:
        fura = cil_z(x, y, BASE_E + POSTE_ALT - POSTE_P - 0.5, POSTE_P + 0.5, 2.8)
        assert (fura ^ P['poste_base']).volume() < tol, ('parafuso', x, y)
    rel['checagens']['parafusos_poste_cabeca_passam'] = 'passou (2 posições)'
    # negativos: Pi com caixa grossa e tela maior que a prevista têm que bater
    grosso = box(PI_X0, PI_X1, Y_PI, Y_PI + PI_PCB + SOBRA_TRAS + 3.5, -PI_H / 2, PI_H / 2)
    n1 = (P['tampa'] ^ grosso).volume()
    tela_grande = box(PI_X0 - 6, PI_X0 + HAT_W + 6, FRENTE_E, FRENTE_E + HAT_E, -HAT_H / 2 - 4, HAT_H / 2 + 4)
    n2 = (P['frente'] ^ tela_grande).volume()
    assert n1 > 1 and n2 > 1, (n1, n2)
    rel['checagens']['negativos_mm3'] = {'pi_mais_grosso_bate_na_tampa': round(n1, 1), 'tela_6mm_maior_bate_na_caixa': round(n2, 1)}
    # estabilidade: massa estimada (PLA 35%), Pi + tela 70 g
    mass, cg = 0.0, np.zeros(3)
    for v in [f_m, t_m, P['poste_base']]:
        m = mesh(v); g = m.volume / 1000 * 1.24 * 0.35; mass += g; cg += g * m.center_mass
    for g, env in [(70.0, mundo_cabeca(pi_placa)), (25.0, mundo_cabeca(tela))]:
        e = mesh(env); mass += g; cg += g * e.center_mass
    cg /= mass
    m_tras, m_frente = BASE_Y1 - cg[1], cg[1] - BASE_Y0
    rel['checagens']['estabilidade'] = {'massa_estimada_g': round(mass), 'centro_de_massa_mm': cg.round(1).tolist(),
                                        'margem_ate_a_borda_traseira_mm': round(m_tras, 1), 'margem_ate_a_borda_dianteira_mm': round(m_frente, 1)}
    assert m_tras > 25 and m_frente > 25
    rel['limites'] = [
        'Estudo: sem fatiamento nem teste físico. As medidas da tela 2,4" são TÍPICAS (formato Pi Zero 65 x 56,5 mm); o anúncio não traz o contorno.',
        'Se a placa da tela tiver o tamanho do Pi (85 x 56 mm) ou outro conector, mude HAT_W/HAT_H/HAT_DX/EMPILHA e rode de novo: os testes mostram se ainda cabe.',
        'A janela está centrada na placa da tela; confira a posição real da área visível.',
        'Os postes de M2,5 (58 x 49 mm) seguram o Pi pela tampa; a tela fica presa só pelo conector de 40 pinos (use espaçadores M2,5 se vier com furos).',
        'O microfone USB sai pela lateral direita; o alto-falante é o da própria placa da tela (áudio por PWM, qualidade simples).',
        'Cabeça reta, sem inclinação. Sem análise de aquecimento do Pi no interior fechado: a tampa tem fendas de ventilação.']
    (OUT / 'verificacao.json').write_text(json.dumps(rel, ensure_ascii=False, indent=2) + '\n')
    return P, f_m, t_m, rel


if __name__ == '__main__':
    P, f_m, t_m, rel = verificar()
    sc = trimesh.Scene()
    cores = {'frente': [24, 24, 30, 255], 'tampa': [215, 166, 55, 255], 'poste': [70, 80, 91, 255]}
    for nome, m, c in [('frente', mesh(f_m), cores['frente']), ('tampa', mesh(t_m), cores['tampa']), ('poste', mesh(P['poste_base']), cores['poste'])]:
        m.visual.face_colors = c; sc.add_geometry(m, node_name=nome)
    sc.export(OUT / 'montagem-ESTUDO.glb')
    print(json.dumps(rel['pecas'], ensure_ascii=False, indent=1)); print(json.dumps(rel['checagens'], ensure_ascii=False, indent=1))
