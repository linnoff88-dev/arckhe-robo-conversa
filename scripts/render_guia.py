"""Renders do guia a partir do CAD real (Blender 4.0, Cycles na CPU).
  blender -b -P scripts/render_guia.py -- <estudo> <saida> [cena ...]
Cenas: conjunto frente lado costas-caixa costas-pi-nu explodida
Nenhum texto é desenhado na imagem; legendas ficam no HTML (3 idiomas).
A imagem na tela é a prévia real do rosto (estudo/rosto-*.png), colada no plano da área visível.
"""
import math, os, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Euler

a = sys.argv[sys.argv.index('--') + 1:]
EST, SAIDA = Path(a[0]), Path(a[1]); QUAIS = set(a[2:]); SAIDA.mkdir(parents=True, exist_ok=True)
MM = 0.001
INCL, ALTURA, ZC = 12.0, 62.0, 85.5


def limpar():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = int(os.environ.get('AMOSTRAS', 160)); sc.cycles.adaptive_threshold = 0.01
    sc.cycles.use_denoising = False
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 12
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1100
    w = bpy.data.worlds.new('m'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.012, 0.012, 0.016, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 1.0


def mat(nome, cor, rug=0.45, coat=0.0, metal=0.0, emissao=None):
    m = bpy.data.materials.new(nome); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*cor, 1); p.inputs['Roughness'].default_value = rug
    p.inputs['Coat Weight'].default_value = coat; p.inputs['Metallic'].default_value = metal
    return m


def stl(caminho, nome, m, graus=35):
    bpy.ops.wm.stl_import(filepath=str(caminho))
    ob = bpy.context.selected_objects[0]; ob.name = nome
    ob.data.transform(Matrix.Scale(MM, 4)); ob.data.materials.append(m)
    for p in ob.data.polygons: p.use_smooth = True
    ob.data.use_auto_smooth = True; ob.data.auto_smooth_angle = math.radians(graus)
    return ob


def luz(nome, loc, alvo, w, tam):
    d = bpy.data.lights.new(nome, 'AREA'); d.energy = w; d.size = tam
    o = bpy.data.objects.new(nome, d); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(alvo) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def chao():
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0.05, -0.0005))
    c = bpy.context.object; c.data.materials.append(mat('mesa', (0.02, 0.02, 0.025), 0.7, 0.0))


def tela_com_rosto(nome_png, deslocamento_y=0.0):
    """Plano emissivo sobre a área visível (155 x 86 mm), no quadro do display, depois inclinado e levantado."""
    bpy.ops.mesh.primitive_plane_add(size=1)
    pl = bpy.context.object
    img = bpy.data.images.load(str(EST / nome_png))
    m = bpy.data.materials.new('rosto'); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Strength'].default_value = 1.6
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(t.outputs['Color'], e.inputs['Color']); nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
    pl.data.materials.append(m)
    R = Euler((math.radians(90), 0, 0)).to_matrix().to_4x4()            # plano de frente para −Y, no quadro do display
    p = Vector((0, -0.05 + deslocamento_y, ZC)) * MM
    cen = Matrix.Rotation(math.radians(-INCL), 4, 'X') @ Matrix.Translation(p) @ R
    pl.matrix_world = Matrix.Translation((0, 0, ALTURA * MM)) @ cen @ Matrix.Diagonal((0.155, 0.086, 1, 1))
    return pl


def cena(nome, ocultar, camera, alvo, lente=50, rosto='rosto-ocioso.png', pasta='partes-mundo', sem_tela=False, extra=None):
    if QUAIS and nome not in QUAIS: return
    limpar()
    cores = {'moldura': mat('mol', (0.015, 0.015, 0.02), 0.28, 0.5), 'placa': mat('pla', (0.12, 0.13, 0.15), 0.5),
             'caixa': mat('cai', (0.12, 0.13, 0.15), 0.5), 'tampa': mat('tam', (0.62, 0.38, 0.03), 0.45, 0.15),
             'pescoco_base': mat('bas', (0.62, 0.38, 0.03), 0.45, 0.15), 'adaptador': mat('ada', (0.10, 0.35, 0.18), 0.5),
             'tela': mat('tel', (0.01, 0.01, 0.012), 0.2), 'caixa_pi': mat('cpi', (0.75, 0.75, 0.72), 0.3, 0.4),
             'driver': mat('dri', (0.05, 0.3, 0.12), 0.5), 'pi_nu': mat('pin', (0.04, 0.32, 0.10), 0.4)}
    for f in sorted((EST / pasta).glob('*.stl')):
        if f.stem in ocultar: continue
        stl(f, f.stem, cores[f.stem])
    if not sem_tela and 'tela' not in ocultar: tela_com_rosto(rosto, -22 * 0 if pasta == 'partes-mundo' else 0)
    chao()
    luz('chave', (0.5, -0.7, 0.7), (0, 0.03, 0.12), 70, 0.5)
    luz('contra', (-0.7, 0.4, 0.5), (0, 0.03, 0.12), 40, 0.5)
    luz('topo', (0, 0.1, 1.2), (0, 0.03, 0.1), 22, 0.8)
    cam = bpy.data.cameras.new('c'); cam.lens = lente
    co = bpy.data.objects.new('c', cam); bpy.context.collection.objects.link(co); bpy.context.scene.camera = co
    co.location = Vector(camera); co.rotation_euler = (Vector(alvo) - co.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.render.filepath = str(SAIDA / f'{nome}.png'); bpy.ops.render.render(write_still=True)
    print('feito', nome, flush=True)


T = {'caixa_pi', 'driver', 'adaptador', 'pi_nu'}
A = (0, 0.03, 0.115)
cena('conjunto', T, (0.55, -0.62, 0.34), A, 45)
cena('frente', T, (0, -0.95, 0.14), A, 50)
cena('lado', T, (0.95, 0.03, 0.12), A, 50)
cena('costas-caixa', {'tampa', 'driver', 'adaptador', 'pi_nu', 'tela'}, (-0.45, 0.55, 0.30), A, 45, sem_tela=True)
cena('costas-pi-nu', {'tampa', 'driver', 'caixa_pi', 'tela'}, (-0.45, 0.55, 0.30), A, 45, sem_tela=True)
cena('explodida', {'caixa_pi', 'driver', 'tela'}, (0.62, 0.30, 0.38), (0, 0.06, 0.13), 40, pasta='partes-explodida', sem_tela=True)
