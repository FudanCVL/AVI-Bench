import json
from . import definitions

havib_constants = definitions.havib_constants

def read_json_to_list(file_path):
    """Read a JSON file and return the data as a list."""
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data if isinstance(data, list) else []


def get_real_options_or_classes(d: dict):
    """ replace the pseudo-options with real options. """

    if 'options' in d['input']['question'].keys():
        options = d['input']['question']['options']

        if options in havib_constants[d['task']].keys():
            options = havib_constants[d['task']][options]

        if options is not None:
            if 'cls' in options:
                opt_or_cls = 'semantic categories'
            else:
                opt_or_cls = 'options'

            options = f'Available {opt_or_cls} are: {options}'
        else:
            options = ''
    else:
        options = ''

    return options

def get_real_prompt(d: dict):
    """ replace the pseudo-prompt with real prompt. """

    prompt = ''
    if 'prompt' in d['input']['question'].keys():
        prompt = d['input']['question']['prompt']

        if prompt in havib_constants[d['task']].keys():  # replace the pseudo-options with real options.
            prompt = havib_constants[d['task']][prompt]

        if prompt is None:
            prompt = ''
    else:
        prompt = ''

    return prompt

def get_real_input(d: dict):
    """ concat input info: text_input = prompt + options + question. """
    prompt = get_real_prompt(d)  # replace the pseudo-prompt with real prompt.
    options = get_real_options_or_classes(d)  # replace the pseudo-options with real options.
    question = d['input']['question']['text']
    text_input = f'{prompt}. {options}. {question}'

    return text_input
