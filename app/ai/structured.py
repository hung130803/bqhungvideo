"""Small explicit schemas with local validation even on non-schema providers."""
import math

STRICT_MODELS = {'openai/gpt-oss-20b', 'openai/gpt-oss-120b',
                 'qwen/qwen3.8-27b', 'meta-models/muse-spark-open'}

EVENTS = {'type': 'object', 'additionalProperties': False,
    'required': ['events'], 'properties': {'events': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False,
        'required': ['id', 'event', 'interest'], 'properties': {
            'id': {'type': 'integer'}, 'event': {'type': 'string'},
            'interest': {'type': 'number'}}}}}}


def validate(value, schema, path='$'):
    """Validate the schema subset owned here. Never coerce malformed AI output."""
    kind = schema['type']
    valid = {'object': lambda: isinstance(value, dict),
             'array': lambda: isinstance(value, list),
             'string': lambda: isinstance(value, str),
             'integer': lambda: type(value) is int,
             'number': lambda: type(value) in (int, float) and math.isfinite(value),
             'boolean': lambda: type(value) is bool}
    if kind not in valid or not valid[kind]():
        raise ValueError(f'{path}: expected {kind}')
    if kind == 'object':
        props = schema['properties']
        if set(schema.get('required', [])) - value.keys():
            raise ValueError(f'{path}: missing fields')
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise ValueError(f'{path}: unknown fields')
        for key in value.keys() & props.keys(): validate(value[key], props[key], path+'.'+key)
    elif kind == 'array':
        for i, item in enumerate(value): validate(item, schema['items'], f'{path}[{i}]')
    return value
