# RobÃ´ conversa

<div align="center">
  <img src="capa/logo.svg" alt="Arckhé AI" height="48" />
  <p><strong>Arckhé AI</strong></p>
</div>


**ðŸ‡§ðŸ‡· [PortuguÃªs](README.md) Â· ðŸ‡ºðŸ‡¸ [English](README.en.md) Â· ðŸ‡ªðŸ‡¸ [EspaÃ±ol](README.es.md)**

[![RobÃ´ conversa](guia/assets/banner.jpg)](https://inematds.github.io/robo-conversa/guia/)

## O que Ã©

Um robÃ´ de mesa que ouve e responde. Um Raspberry Pi 3 fica atrÃ¡s da tela oficial de 7 polegadas, num suporte impresso em 3D que se prende na mesa. Na tela roda um rosto animado (olhos e boca amarelos). VocÃª toca, fala, e o Pi manda a sua voz ao seu servidor Jarvis, toca a resposta e mexe a boca no ritmo dela. O suporte serve para o Pi com caixa e para o Pi sem caixa.

**Estado honesto:** o desenho 3D e o software foram verificados no computador (checagens geomÃ©tricas e 4 testes automÃ¡ticos com um Jarvis de mentira). Nada foi impresso, fatiado nem ligado numa tela ou microfone reais. A rota `/conversa` ainda nÃ£o existe no Jarvis de ninguÃ©m: o contrato estÃ¡ no guia.

## Guia e downloads

**https://inematds.github.io/robo-conversa/guia/**

Tem render do modelo real, modelo 3D girÃ¡vel, medidas, lista de materiais, STL, ZIP das peÃ§as, ZIP do software, passo a passo de impressÃ£o, montagem e software.

## O processo, do inÃ­cio ao fim

Quem faz: ðŸ§  sessÃ£o com o Nei Â· âš™ï¸ script Â· ðŸ¤– `claude -p`.

1. ðŸ§  Decidir tela, Pi e como usar (com/sem caixa). Medidas e limites em `cad/gerar.py` (parÃ¢metros no topo).
2. âš™ï¸ Gerar as peÃ§as e a verificaÃ§Ã£o: `../robos-impressos/.venv/bin/python cad/gerar.py` (grava `estudo/`: STL, GLB, `verificacao.json`, `partes-mundo/`, `partes-explodida/`). Para na primeira checagem que falhar.
3. âš™ï¸ PrÃ©via rÃ¡pida das peÃ§as: `blender -b -P scripts/previa.py -- estudo/partes-mundo estudo/previa`.
4. âš™ï¸ PrÃ©via do rosto: `chromium --headless=new --screenshot=estudo/rosto-<estado>.png "file://$PWD/software/rosto/index.html?estado=<estado>"`; montar `estudo/rosto-estados.png` (contato de 5 estados).
5. âš™ï¸ Renders finais (Blender, CPU, ~4 min), pela vaga de render: `~/projetos/wifi/scripts/fila-vaga render robo-conversa -- env AMOSTRAS=320 blender -b -P scripts/render_guia.py -- estudo estudo/renders`; copiar para `guia/assets/r-*.jpg`.
6. âš™ï¸ Banners a partir do render real: `python3 scripts/banners.py` (sem arte de IA: o robÃ´ ainda nÃ£o foi impresso).
7. ðŸ§  Software: `python3 software/testes/test_ponte.py` (4 testes; sobe Jarvis falso, confere estados, token, boca e queda do servidor).
8. ðŸ§  Copiar STL, GLB e `verificacao.json` para `guia/downloads/` e refazer os dois ZIP (peÃ§as e software).
9. ðŸ§  Escrever o guia PT (`python3 scripts/monta_guia.py` â†’ `guia/index.html`); âš™ï¸ traduzir para EN/ES: `python3 ~/projetos/wifi/scripts/traduz-pagina-codex.py html --base guia --pages index.html --langs en es --site-url https://inematds.github.io/robo-conversa/guia/` e depois `python3 scripts/pos_guia.py`.
10. ðŸ¤– Revisor independente do guia; conferir 360 px e 1280 px por HTTP local.
11. ðŸ§  Commit e push (autor inematds); o GitHub Pages publica sozinho. Push pelo SSH (o token HTTPS nÃ£o tem escopo `workflow`).
12. ðŸ§  Portal (inema.club) e tÃ³pico INEMA.ROBOT; vÃ­deo do guia entra depois na marca `<!-- VIDEO -->`.
13. ðŸ§  VersÃ£o compacta (tela de 2,4â€³ no GPIO, microfone USB): `../robos-impressos/.venv/bin/python cad/gerar_compacta.py` (grava `estudo/compacta/`); rosto na tela pequena: `python3 software/testes/test_rosto_fb.py` (7 testes) e `python3 software/rosto/rosto_fb.py --png <estado> x.png`.
14. ðŸ§  Pendente: imprimir, medir (a tela de 2,4â€³ estÃ¡ com medidas TÃPICAS) e montar; expor `/conversa` no Jarvis; teste real com microfone e alto-falante.

## Arquivos

- `cad/gerar.py`: gera as 7 peÃ§as da versÃ£o grande (tela de 7â€³, com bolso de microfone e caixa de alto-falante), a montagem e as checagens.
- `cad/gerar_compacta.py`: versÃ£o compacta (Pi 3 + tela de 2,4â€³ + microfone USB): 3 peÃ§as e checagens.
- `software/rosto/`: rosto animado (HTML) e `rosto_fb.py` (rosto direto no framebuffer de telas pequenas). `software/ponte/robo.py`: ponte do Pi (sÃ³ biblioteca padrÃ£o). `software/ponte/jarvis_falso.py`: servidor de teste.
- `guia/`: pÃ¡gina PT/EN/ES, imagens e downloads.
- `referencias/dimensoes.md`: de onde vem cada medida.

---

<div align="center">
  <img src="capa/logo.svg" alt="Arckhé AI" height="32" />
  <p><strong>Arckhé AI</strong></p>
</div>