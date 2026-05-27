import json
from definitions import havib_constants

def read_json_to_list(file_path):
    """Read a JSON file and return the data as a list.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        list: A list of data from the JSON file, or an empty list if the data is not a list.
    """
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



if __name__ == '__main__':
    # pre code: ... sample one data d ...
    d = {
        "id": "00000",
        "task": "AVLG",
        "subtask": None,
        "input": {
            "pre_question": None,
            "question": {
                "prompt": "prompt_avlg",
                "text": "Segment the object in the given framse based on the given text reference. Reference: The sounding object near the man.",
                "options": None
            },
            "image_list": [
                "./input/images/89wbeFGWzkY_415000_425000/0.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/1.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/2.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/3.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/4.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/5.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/6.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/7.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/8.jpg",
                "./input/images/89wbeFGWzkY_415000_425000/9.jpg"
            ],
            "audio_list": [
                "./input/wavs/89wbeFGWzkY_415000_425000.wav"
            ]
        },
        "output": {
            "pre_answer": None,
            "question_answer": {
                "frame_0": [
                    705,
                    359,
                    353,
                    229
                ],
                "frame_1": [
                    699,
                    360,
                    373,
                    230
                ],
                "frame_2": [
                    703,
                    358,
                    408,
                    232
                ],
                "frame_3": [
                    705,
                    367,
                    451,
                    223
                ],
                "frame_4": [
                    690,
                    345,
                    422,
                    244
                ],
                "frame_5": [
                    684,
                    354,
                    388,
                    235
                ],
                "frame_6": [
                    683,
                    356,
                    351,
                    234
                ],
                "frame_7": [
                    695,
                    363,
                    374,
                    227
                ],
                "frame_8": [
                    704,
                    360,
                    422,
                    230
                ],
                "frame_9": [
                    688,
                    344,
                    467,
                    246
                ]
            }
        }
    }
    # print(d['input'])

    _input = get_real_input(d)
    print(_input)
