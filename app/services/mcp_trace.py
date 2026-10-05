"""Traza estructurada del pipeline del chat MCP.

El stream `/mcp/chat/stream` acumula los pasos del pipeline (ruteo, tool,
resultado, síntesis, guard) y los envía:

* embebidos en cada evento ``thinking`` (payload ``step``), para que el
  frontend pueda pintar la tarjeta "Pensamiento y herramientas" en vivo; y
* íntegros en el evento final ``done`` como ``trace``, para que la tarjeta
  siga visible (colapsada) después de responder.

Los eventos legacy conservan su payload original (``content``), así que los
frontends actuales siguen funcionando sin cambios.
"""

from __future__ import annotations

import json

# kind: route    -> decisión de intención / ruteo
#       tool     -> llamada a una función
#       result   -> resultado de la función
#       synth    -> redacción de la respuesta final
#       guard    -> corrección anti-alucinación de datos
#       confirm  -> esperando confirmación humana
TRACE_KINDS = ('route', 'tool', 'result', 'synth', 'guard', 'confirm')


class TraceBuilder:
    """Acumula pasos del stream y arma los eventos SSE relacionados."""

    def __init__(self) -> None:
        self._steps: list[dict] = []

    def add(self, kind: str, text: str, tool: str | None = None, ok: bool | None = None) -> dict:
        if kind not in TRACE_KINDS:
            kind = 'route'
        step: dict = {'kind': kind, 'text': text}
        if tool:
            step['tool'] = tool
        if ok is not None:
            step['ok'] = ok
        self._steps.append(step)
        return step

    def as_list(self) -> list[dict]:
        return list(self._steps)

    def thinking(self, content: str, kind: str = 'route', tool: str | None = None) -> str:
        """Evento ``thinking`` legacy + ``step`` estructurado (SSE ``data:``)."""
        step = self.add(kind, content, tool=tool)
        return _sse({'type': 'thinking', 'content': content, 'step': step})

    def tool_call(self, name: str, args: dict) -> None:
        self.add('tool', f'Ejecutando {name}({json.dumps(args, ensure_ascii=False)})', tool=name)

    def tool_result(self, name: str, success: bool) -> None:
        self.add('result', f'Resultado de {name}', tool=name, ok=success)


def _sse(payload: dict) -> str:
    return f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'
