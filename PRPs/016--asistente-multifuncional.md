# PRP 016 — Asistente multifuncional (fotos, documentos, informes y modelo a elección)

## Por qué
El asistente del centro ya habla con MiMo (opencode) y las herramientas MCP, pero:
- la cuota gratis de MiMo se acaba seguido y el chat quedaba «pensando» sin decir nada;
- no se le pueden mandar fotos (comprobantes) ni documentos;
- no arma informes de un alumno (sesiones, evolución, informe terapéutico).

## Límites de opencode que el diseño respeta
- **Cuota gratis**: cuando se acaba, OpenCode reintenta sin devolver el error. Se detecta mirando
  `GET /session/status` mientras se espera (PR #101) y se pausa MiMo 1 h. La persona ve una barra abajo
  («MiMo sin cuota · responder con …») y elige otro modelo de la cadena (Groq, Gemini, Ollama…).
- **Visión**: MiMo lee imágenes; si no está, el OCR de respaldo (Gemini/Groq visión) de `/mcp/upload`.
- **Sin archivos ni comandos del servidor**: todo pasa por herramientas MCP de la lista blanca.
- **Tiempo**: Cloudflare corta a los 100 s; todo lo que espera a un modelo va por SSE con latido.
- **Contexto**: los documentos largos se recortan (primeros ~12 000 caracteres) antes de pedir el resumen.

## Escalabilidad
- Cada capacidad es una herramienta MCP (`patient_report`, `drive_save_upload`, `print_drive_file`,
  `schedule_patient_plan`): la usan el asistente, el chat flotante, Telegram y la IA de cualquier proveedor.
- El análisis de adjuntos es un servicio (`assistant_files`) independiente del modelo: cambia el modelo,
  no el flujo.
- La preferencia de modelo es por petición (contextvar en `llm_client`), no global: no afecta a otros usuarios.

## Fases
1. **(este PR)** Barra de modelo y selector · fotos → formulario de pago/gasto · documentos → resumen,
   guardar en Drive e imprimir · informe del alumno en TXT (datos, contrato, todas las sesiones, juegos,
   asistencia, evolución e informe terapéutico redactado por la IA) · impresora por USB.
2. Informe en DOCX/PDF con el membrete del centro; informes por grupo y por sede.
3. Audio (nota de voz → transcripción con Whisper ya existente → pregunta).
4. Memoria por paciente (resúmenes de conversaciones pasadas indexados para preguntas de seguimiento).

## Impresora por USB
`moscowle_scand` solo buscaba la Epson en la red. Si está conectada por USB, CUPS la ve como `usb://EPSON/...`
(`lpinfo -v`): `repair` ahora la usa cuando no la encuentra en la red. Hay que volver a correr
`deploy/scanner/setup_scanner.sh` en el host para actualizar el servicio.
