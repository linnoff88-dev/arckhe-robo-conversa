"""Prévia rápida (Workbench) das peças em posição de montagem.
blender -b -P scripts/previa.py -- estudo/partes-mundo estudo/previa
"""
import sys, math
from pathlib import Path
import bpy
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
src, out = Path(a[0]), Path(a[1]); out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'OBJECT'
sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
cores = {'moldura': (.08,.08,.10), 'placa': (.27,.31,.36), 'caixa': (.27,.31,.36), 'tampa': (.85,.65,.2),
         'pescoco_base': (.85,.65,.2), 'tela': (.02,.02,.03), 'caixa_pi': (.9,.9,.88), 'driver': (.1,.5,.3), 'adaptador': (.3,.6,.4)}
ocultar = set(a[2:]) if len(a) > 2 else {'caixa_pi', 'driver', 'tela', 'adaptador'}
for f in sorted(src.glob('*.stl')):
    n = f.stem
    if n in ocultar: continue
    bpy.ops.wm.stl_import(filepath=str(f))
    ob = bpy.context.selected_objects[0]
    ob.scale = (.001,)*3
    ob.color = (*cores.get(n,(.5,.5,.5)), 1)
cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
def tira(nome, loc, alvo, esc):
    co.location = Vector(loc); d = Vector(alvo) - co.location
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); cam.ortho_scale = esc
    sc.render.filepath = str(out / f'{nome}.png'); bpy.ops.render.render(write_still=True)
c = (0, .05, .11)
tira('topo', (0, .02, 2), (0, .02, 0), .34)
tira('base-perto', (0, -1.2, .6), (0, -.03, .01), .12)
tira('frente', (0, -2, .11), c, .34)
tira('lado', (2, .05, .11), c, .34)
tira('costas', (0, 2, .11), c, .34)
tira('persp', (.8, -1.0, .6), c, .34)
tira('persp-costas', (-.8, 1.0, .6), c, .34)
if len(a) > 2 and a[2] == 'topo':
    pass
