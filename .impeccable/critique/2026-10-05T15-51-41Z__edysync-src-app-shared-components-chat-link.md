---
target: app-chat-link y su integracion en el menu de preferencias
total_score: 21
max_score: 40
na_heuristics:
p0_count: 0
p1_count: 6
target_identity: "file:/Users/apple/Documents/moscowle_ia/edysync/src/app/shared/components/chat-link"
timestamp: 2026-10-05T15-51-41Z
slug: edysync-src-app-shared-components-chat-link
---
Method: dual-agent (A: revision de diseno, B: detector + auditoria tecnica). Navegador omitido: sin app corriendo ni sesion.

# Critique app-chat-link: 21/40 (Acceptable) | Audit 11/20 (Acceptable)

Especificidad: intercambiable (SaaS generico con login por bot; sin verde oliva de marca). Detector: 0 hallazgos, pero no ve foco, contraste por token ni tamano de objetivo tactil.

## Prioridades (0 P0, 6 P1)
- P1 Foco de teclado invisible (button.scss:88-91, outline:none) -> harden
- P1 Boton primario sin contraste: 2.83:1 claro, 1.75:1 oscuro (--color-on-primary solo definido una vez) -> colorize
- P1 Objetivos tactiles de 36px (<44) y Confirmar/Cancelar a 4px; cierre de alerta 20x20 sin aria-label -> harden
- P1 Foco perdido al confirmar/cancelar desvinculacion (@if/@else destruye el boton) -> harden
- P1 Cerrar el menu pierde el codigo (@if (open)); dos filas de Telegram con fuentes distintas -> distill
- P1 Viaje entre apps sin guiar: sin nombre del bot ni enlace directo -> clarify

## P2
- Copiar nunca funciona en LAN HTTP (navigator.clipboard)
- "Vincular otro chat" no detecta el nuevo vinculo (compara linked, ya true)
- .btn-spinner sin CSS en todo el proyecto
- Vencido con opacity .6: timer 3.05:1
- Sondeo sin guardas (errores tragados, sigue con pestana oculta)
- Menu w-80 fijo en pantallas de 320px
