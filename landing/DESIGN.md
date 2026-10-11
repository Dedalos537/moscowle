# DESIGN — Landing centrojuanpabloii.com

Derivado de lo construido (`landing/src/styles.css`, `landing/src/three/`). Describe el sistema tal como está; si
el código cambia, este archivo se actualiza con él.

## Mundo

Bloques lógicos de madera pintada (círculo, cuadrado, triángulo, rectángulo), el material concreto con el que
trabajan las terapeutas, sobre un campo oliva profundo. Fuera del hero y del cierre, la página es blanca con paneles
salvia. Luz de día: las familias la leen en el celular, de día, en Piura.

## Color

| Token | Valor | Uso |
|---|---|---|
| `--olive-800` | `#2c4214` | Campo del hero, barra superior y sección Agendar |
| `--olive-950` | `#172409` | Pie de página; texto sobre lima |
| `--olive-500` | `#81a141` | Verde del logo; pasos alcanzados, bloques |
| `--lime` | `#c4d228` | Botón principal sobre oliva, línea destacada del hero, foco sobre oscuro |
| `--sage-50` / `--sage-100` | `#f3f6ea` / `#e6eed4` | Fondos de Terapias, Preguntas y Nosotros |
| `--coral` / `--cobalt` | `#e25f43` / `#2f6fb5` | Solo bloques 3D y glifos; nunca texto. Cobalto es el anillo de foco sobre claro |
| `--wa` | `#157a42` | Botones de WhatsApp (blanco encima: 5.4:1) |
| `--ink` / `--ink-2` / `--ink-3` | `#18210d` / `#485536` / `#5d6a4a` | Texto; todos ≥ 5.2:1 sobre blanco y salvia |

Bordes de campos `#84946a` (3.3:1, cumple 1.4.11). Estrategia: comprometida, porque el oliva ocupa los extremos de
la página y el resto respira.

## Tipografía

- **Bricolage Grotesque Variable** (opsz/wght), display: titular del hero en 800 con tracking −0.03em; h2 en 760.
- **Atkinson Hyperlegible Next**, texto: elegida por legibilidad para baja visión, que es parte del público del centro.
- Autoalojadas con fontsource (sin terceros).

## Componentes

- Botones redondeados (999px), mínimo 3.25rem de alto: `--lime`, `--ghost-light`, `--wa`, `--outline`, `--dark`.
- Terapias: pestañas por categoría con su glifo de bloque y filas desplegables (no tarjetas iguales).
- Cifras: lista con glifo + número tabular, junto a la torre 3D (no tiles de métricas).
- Agendar: panel blanco sobre oliva con selector, horario segmentado y tres salidas (WhatsApp, llamar, que me llamen).
- Barra fija inferior en el celular con Llamar / WhatsApp, oculta mientras se ve el hero o la sección Agendar.

## Movimiento

Un solo lenguaje: los bloques. Hero con flotación de periodo propio por bloque y parallax al puntero; recorrido
de la evaluación guiado por el scroll (firma); torre que se apila una vez al entrar. Easing exponencial de salida.
three.js se carga en diferido, pausa fuera de pantalla, densidad de píxeles ≤ 1.75; `prefers-reduced-motion` pinta
un único cuadro final y sin WebGL se muestra una versión plana en SVG.

## Reglas

- Sin fotos de stock: las imágenes de terapias son opcionales y deben ser reales del centro (se cargan desde el admin).
- Sin eyebrows sobre títulos, sin texto en degradado, sin tarjetas anidadas.
- El contenido se edita desde Configuración › Equipo › Sitio web; los textos por defecto viven en
  `app/data/landing_default.json`.
