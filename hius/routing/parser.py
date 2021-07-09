import re
from uuid import UUID
from typing import Tuple, Dict, Pattern, Callable
from hius.routing.utils import Converter


PARAM_REGEX = re.compile(r'(.*){([a-zA-Z_][\w]*)(:.+)?}(.*)')
PARAM_COVERTERS = {
    'path': Converter(r'.*', str),
    'str': Converter(r'[^/]+', str),
    'int': Converter(r'\d+', int),
    'float': Converter(r'\d+(\.\d+)?', float),
    'uuid': Converter(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-'
                      r'[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', UUID)
}


def _unpack(match: re.Match) -> Tuple[str, str, str, str]:
    head, name, type, tail = match.groups(default='str')
    return head, name, type.lstrip(':'), tail


def _get_converter(param_type: str) -> Converter:
    return PARAM_COVERTERS.get(param_type, Converter(param_type))


def parse_path(path: str) -> Tuple[str, Pattern, Dict[str, Callable]]:
    path_segments = []
    regex_segments = ['^']
    param_convertors = {}
    dup_params = set()

    for segment in path.lstrip('/').split('/'):
        match = PARAM_REGEX.match(segment)
        if not match:
            regex_segments.append(re.escape(segment))
            path_segments.append(segment)
            continue

        segment_head, param_name, param_type, segment_tail = _unpack(match)
        convertor = _get_converter(param_type)

        regex_segments.append(f'{re.escape(segment_head)}'
                              f'(?P<{param_name}>{convertor.regex})'
                              f'{re.escape(segment_tail)}')

        path_segments.append(f'{segment_head}{{{param_name}}}{segment_tail}')

        if param_name in param_convertors:
            dup_params.add(param_name)
        param_convertors[param_name] = convertor

    if dup_params:
        raise ValueError(f'duplicated params at path {path}: {dup_params}')

    path = '/' + '/'.join(path_segments)
    pattern = re.compile('/'.join(regex_segments) + '$')
    return path, pattern, param_convertors
