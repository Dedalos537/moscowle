"""Formatos de llamada a funciones del LLM.

Regresión del bug de producción: el modelo pequeño emite la llamada con
paréntesis en vez de ángulos — ``(function=list_patients {...})`` — y ni el
parser ni la limpieza la reconocían, así que la llamada cruda se filtraba a la
burbuja del chat junto con datos alucinados.
"""

from app.services.mcp_service import (
    _UNKNOWN_CALL_RE,
    _parse_text_tool_call,
    strip_tool_calls,
)


def test_canonical_angle_format_parses():
    name, args = _parse_text_tool_call('<function=list_patients{"limit": 5}</function>')
    assert name == 'list_patients'
    assert args == {'limit': 5}


def test_paren_format_with_json_args_parses():
    """El formato que filtró producción: (function=nombre {...})."""
    raw = (
        'Tengo 5 terapeutas registrados en el sistema.\n\n'
        '(function=list_patients {"include_inactive":{"type":"boolean"}})'
    )
    name, args = _parse_text_tool_call(raw)
    assert name == 'list_patients', 'el parser debe reconocer la variante con paréntesis'
    assert args == {'include_inactive': {'type': 'boolean'}}


def test_paren_format_simple_args_parses():
    name, args = _parse_text_tool_call('(function=list_patients {"limit": 5})')
    assert name == 'list_patients'
    assert args == {'limit': 5}


def test_paren_format_without_args_parses():
    name, args = _parse_text_tool_call('(function=list_users)')
    assert name == 'list_users'
    assert args == {}


def test_paren_format_unknown_tool_is_not_executed():
    """Un nombre fantasma (list_therapists) no debe ejecutarse: queda para el
    guard de re-prompt y la limpieza."""
    name, args = _parse_text_tool_call('(function=list_therapists {"role": "terapista"})')
    assert name is None


def test_strip_removes_both_formats():
    text = (
        'Respuesta previa. '
        '<function=list_users{"role": "terapista"}></function> '
        'y también (function=list_patients {"limit": 5}) '
        'sigue el texto normal.'
    )
    cleaned = strip_tool_calls(text)
    assert 'function=' not in cleaned
    assert 'Respuesta previa.' in cleaned
    assert 'sigue el texto normal.' in cleaned


def test_strip_leaves_plain_text_untouched():
    text = 'Hay 5 terapeutas y 12 pacientes activos.'
    assert strip_tool_calls(text) == text


def test_unknown_call_regex_matches_both_variants():
    """El guard de herramientas fantasma debe ver las dos sintaxis."""
    m = _UNKNOWN_CALL_RE.search('lo pido <function=list_therapists{"x":1}</function>')
    assert m and m.group(1) == 'list_therapists'
    m = _UNKNOWN_CALL_RE.search('lo pido (function=list_therapists {"x": 1})')
    assert m and m.group(1) == 'list_therapists'
    assert _UNKNOWN_CALL_RE.search('sin llamadas aquí') is None
