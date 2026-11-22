"""Banners do guia a partir do render real (sem arte de IA: o robô ainda não foi impresso)."""
from PIL import Image, ImageDraw, ImageFont
B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; R = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def banner(t1, t2, out, grade):
    W, H = 1600, 900
    r = Image.open('estudo/renders/conjunto.png').convert('RGB'); r = r.resize((int(r.width * .9), int(r.height * .9)))
    im = Image.new('RGB', (W, H), '#0c0c10')
    m = Image.new('L', r.size, 255)
    for x in range(330): m.paste(int(255 * x / 330), (x, 0, x + 1, r.height))   # esmaece a borda esquerda
    im.paste(r, (330, -45), m)
    d = ImageDraw.Draw(im); f1 = ImageFont.truetype(B, 72); f2 = ImageFont.truetype(R, 34)
    y = 230
    for l in t1: d.text((70, y), l, font=f1, fill='#FACC15'); y += 90
    y += 24
    for l in t2: d.text((70, y), l, font=f2, fill='#f1f1f3'); y += 48
    d.text((70, 810), 'INEMA.CLUB', font=f2, fill='#FACC15')
    im.save(out, quality=88, optimize=True)
    im.resize((1200, 675)).save(grade, quality=86, optimize=True)
banner(['Robô que', 'conversa na', 'sua mesa'], ['Raspberry Pi 3 + tela de 7"', 'Suporte impresso em 3D'], 'guia/assets/banner.jpg', 'guia/assets/banner-grade.jpg')
banner(['A robot that', 'talks on your', 'desk'], ['Raspberry Pi 3 + 7" screen', '3D-printed stand'], 'guia/assets/banner-en.jpg', 'guia/assets/banner-grade-en.jpg')
banner(['Un robot que', 'conversa en', 'tu mesa'], ['Raspberry Pi 3 + pantalla de 7"', 'Soporte impreso en 3D'], 'guia/assets/banner-es.jpg', 'guia/assets/banner-grade-es.jpg')
