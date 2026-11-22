# De onde vem cada medida

| Medida | Valor usado | Fonte |
|---|---|---|
| Tela oficial Raspberry Pi 7" (800×480), contorno | 192,96 × 110,76 mm (modelo usa 194 × 111 com folga) | https://www.raspberrypi.com/documentation/accessories/display.html |
| Tela, área visível | 155 × 86 mm (janela da moldura 158 × 90) | idem; folha de dados https://datasheets.raspberrypi.com/display/7-inch-display-product-brief.pdf |
| Touch Display 2 (NÃO é a de referência) | 189,5 × 120 mm | documentação oficial; mudar parâmetros em `cad/gerar.py` |
| Raspberry Pi 3 B | placa 85 × 56 mm; furos M2,5 em 58 × 49 mm | desenho mecânico oficial do Pi 3 |
| Caixa do Pi | limite 98 × 68 × 30,5 mm (bolso 100 × 72 × 44 mm) | escolha de projeto; o usuário mede a sua caixa |
| Placa do driver da tela | vão reservado 104 × 72 × 10 mm | estimativa de projeto (placa tem formato do Pi); conferir |

Posição da área visível dentro do contorno, conectores, furos reais e parafusos da tela: NÃO conferidos, só estimados. Medir com paquímetro.
