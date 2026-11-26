# Robô conversa

Leia README.md (seçêo "O processo") antes de agir.

- Raspberry Pi 3 + tela oficial de 7" + suporte impresso em 3D, rosto animado, conversa com o Jarvis do Nei por `POST <JARVIS_URL>/conversa`. Sem Arduino.
- Peças de ESTUDO: nada impresso nem montado; nêo chamar de finais.
- O robô só chama o servidor de `JARVIS_URL`. Sem APIs externas sem autorizaçêo explícita; nenhuma chave no repo.
- Duas versões: grande (7″, `cad/gerar.py`, com bolso de microfone e caixa de alto-falante) e compacta (2,4″ no GPIO + microfone USB, `cad/gerar_compacta.py`, rosto em `software/rosto/rosto_fb.py`). Medidas da tela de 2,4″ sêo TÍPICAS até alguém medir.
- Gerar e conferir: `../robos-impressos/.venv/bin/python cad/gerar.py`; testes: `python3 software/testes/test_ponte.py` e `python3 software/testes/test_rosto_fb.py`.
- Autor dos commits: inematds <inematds@gmail.com>. Push por SSH (workflow).
- Vídeo do guia: entra depois na marca `<!-- VIDEO -->` (explicavideo com avatar, 3 idiomas).
