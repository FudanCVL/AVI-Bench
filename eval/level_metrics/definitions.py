# All definitions and constants

# Task name -> category mapping
TASK_TO_CATEGORY = {
    'ASQA': 'sensation',
    'VSQA_I': 'sensation',
    'VSQA_V': 'sensation',
    'AVSQA': 'sensation',
    'AMIC': 'perception',
    'VMIC': 'perception',
    'AVL': 'perception',
    'AVM': 'perception',
    'VAR': 'understand',
    'AVR': 'understand',
    'AVC': 'understand',
    'AVH': 'reasoning',
    'VAH': 'reasoning',
    'AVQA': 'reasoning',
    'AVLG': 'reasoning',
}

amic_cls_list = ['bus', 'hair-dryer', 'pipa', 'man', 'ambulance', 'razor', 'harp', 'tabla', 'bass', 'handpan',
        'girl', 'sitar', 'car', 'lion', 'guitar', 'vacuum-cleaner', 'cat', 'mower', 'helicopter', 'boy', 'drum',
        'keyboard', 'tuba', 'saw', 'flute', 'cello', 'woman', 'gun', 'accordion', 'violin', 'clarinet', 'erhu',
        'saxophone', 'guzheng', 'dog', 'baby', 'horse', 'male', 'wolf', 'bird', 'ukulele', 'piano', 'female',
        'marimba', 'not sure', 'no available option']

vmic_cls_list = ['sushi', 'banana', 'cake', 'butterfly', 'bird', 'microphone', 'hamburger', 'pineapple',
        'man', 'book', 'sunglasses', 'goat', 'tie', 'cabinetry', 'motorcycle', 'drawer', 'strawberry',
        'sheep', 'pasta', 'parrot', 'bull', 'table', 'penguin', 'watch', 'pillow', 'shellfish', 'kangaroo',
        'flower', 'paddle', 'rocket', 'helicopter', 'bus', 'mushroom', 'bee', 'tree', 'boat', 'saxophone',
        'football', 'lizard', 'violin', 'dog', 'cucumber', 'cello', 'airplane', 'horse', 'drum', 'box',
        'rabbit', 'car', 'door', 'orange', 'shelf', 'camera', 'poster', 'lemon', 'cat', 'fish', 'bread',
        'piano', 'apple', 'glasses', 'bicycle', 'truck', 'deer', 'woman', 'wheelchair', 'cheese', 'chair',
        'plate', 'tomato', 'bed', 'starfish', 'balloon', 'bottle', 'crab', 'beer', 'frog', 'shrimp', 'tower',
        'guitar', 'pig', 'peach', 'train', 'pumpkin', 'elephant', 'jellyfish', 'parachute', 'monkey', 'flag',
        'not sure', 'no available option']


pmp_avl_ans_format = "answer={'category1_id1': '[x_min, y_min, x_max, y_max]', 'category2_id2': '[x_min, y_min, x_max, y_max]'}"
avl_cls_list = ['dog', 'clarinet', 'banjo', 'cat', 'guzheng', 'tree', 'lion', 'tuba',
        'ukulele', 'flute', 'piano', 'person', 'violin', 'airplane', 'bass', 'pipa',
        'trumpet', 'accordion', 'saxophone', 'car', 'lawn-mower', 'cello', 'bassoon',
        'horse', 'guitar', 'erhu', 'not sure', 'no available option']
prompt_avl = f"""
        ctaegories list: {avl_cls_list}
        (1) There may be multiple sounding instances, you can choose instance categories from the given categories list.
        (2) The naming format for instances is: category_id. Instance IDs start from 1, e.g., male_1, dog_2, dog_3, cat_4.
        (3) The bbox format is: [x_min, y_min, x_max, y_max], where x_min, y_min represent the coordinates of the top-left corner.
        (4) The bbox values should be normalized into the range of 0 and 1, e.g., [0.1, 0.12, 0.26, 0.14].
        Do not explain, you must strictly follow the format: {pmp_avl_ans_format}
    """

prompt_avlg = """
        Please output the answer in a format that strictly matches the following example, do not explain:
        answer={'frame_0': [x0_min, y0_min, x0_max, y0_max], 'frame_1': None, ..., 'frame_9': [x9, y9, w9, h9]}.
        Note,
        (1) x_min, y_min represent the coordinates of the top-left corner, while x_max, y_max for the bottom_right corner.
        (2) The bbox values should be normalized into the range of 0 and 1, e.g., [0.1, 0.12, 0.26, 0.14].
        (3) Frames should be ranged from frame_0 to frame_9.
    """

avqa_cls_list = ['ukulele', 'cello', 'clarinet', 'violin', 'bassoon', 'accordion', 'banjo', 'tuba', 'flute', 'electric_bass', 'bagpipe',
        'drum', 'congas', 'suona', 'xylophone', 'saxophone', 'guzheng', 'trumpet', 'erhu', 'piano', 'acoustic_guitar', 'pipa', 'not sure', 'no available option']

havib_constants = {
    'ASQA': {
        'options_sound_clarity': ['first', 'last', 'same', 'not sure'],
        'options_sound_order': ['sound', 'noise', 'not sure'],
        'options_sound_volume': ['first', 'last', 'same', 'not sure'],
        'options_yes_no': ['yes', 'no', 'not sure'],
    },

    'VSQA_I': {
        'get_from_background_binary': ['yes', 'no', 'not sure'],
        'get_from_image_binary': ['yes', 'no', 'not sure'],
        'get_from_foreground_binary': ['yes', 'no', 'not sure'],
        'get_from_image_triple': ['blurred', 'normal', 'clear', 'not sure'],
        'get_from_3d-task1': ['center', 'left', 'right', 'not sure'],
        'get_from_3d-task2': ['cone', 'cube', 'cylinder', 'cuboid', 'no available option', 'not sure'],
        # 'get_from_3d-task3': [0, 1, 2, 3, 4, 5, 6],
        'get_from_space_hard': ['center', 'top left', 'top center', 'top right', 'bottom left', 'bottom center', 'bottom right', 'no available option', 'not sure'],
        'get_from_color': ['blue', 'green', 'red', 'puprle', 'yellow', 'no available option', 'not sure'],
        'get_yes_no': ['yes', 'no', 'not sure'],
        # 'get_lines_count': [0, 1, 2, 3, 4],
        'get_lines_direction': ['horizontal', 'vertical', 'inclined', 'not sure'],
        'get_from_space_easy_area': ['the right one', 'the left one', 'the middle one', 'the bottom one', 'the top one'],
        'get_from_space_easy_bbrightness': ['the right one', 'the left one', 'the middle one', 'the bottom one', 'the top one'],
        'options_yes_no': ['yes', 'no', 'not sure'],
    },

    'VSQA_V': {
        'which_object': ['square', 'circle', 'triangle', 'not sure', 'no available option', 'not sure'],
        'what_shape': ['Triangular pyramid', 'Cone', 'Cube', 'Sphere', 'None', 'not sure'],
        # 'how_many': [0, 1, 2, 3, 4, 5, 6, 7, 8],
        'what_movement_2d': ['horizontal', 'inclined', 'vertical', 'no movenment', 'None', 'not sure'],
        'what_movement_3d': ['Rotation', 'Shrinking', 'Translation', 'Enlarging', 'None', 'not sure'],
        'what_surface': ['Rough', 'Moderate', 'Smooth', 'None', 'not sure'],
        'spacial_change': ['Bottom-left to top-right', 'Bottom-right to top-left', 'Top-left to bottom-right', 'Top-right to bottom-left', 'None', 'not sure', 'No movement',],
        'options_yes_no': ['yes', 'no', 'not sure'],
    },

    'AMIC': {
        'amic_cls_list': amic_cls_list,
        'prompt_amic': "There may be one or more sound-emitting objects in the provided audio. \nPlease strictly output the answer in the format answer={'cls_1': count_1, 'cls_2': count_2}, \nfor example, answer={'dog': 2, 'cat': 3, 'male': 1}. \n"
    },

    'VMIC': {
        'vmic_cls_list': vmic_cls_list,
        'prompt_vmic': "There may be one or more visible objects in the provided image. \nPlease strictly output the answer in the format answer={'cls_1': count_1, 'cls_2': count_2}, \nfor example, answer={'dog': 2, 'cat': 3, 'male': 1}. \n Possible categoris are in the list: vmic_cls_list"
    },

    'AVH': {
        'prompt_avh': "Please answer the question based on the given audio and video.",
        'avh_options_list': ['yes', 'no', 'not sure'],
    },

    'VAH': {
        'prompt_vah': "Please answer the question based on the given audio and video.",
        'vah_options_list': ['yes', 'no', 'not sure'],
    },

    'AVL': {
        'prompt_avl': prompt_avl,
        'avl_cls_list': avl_cls_list,
    },

    'AVM': {
        'prompt_avm': 'Please answer the question based on the given audio and video.',
        'avm_options_list': ['yes', 'no', 'not sure'],
    },

    'AVR': {
        'prompt_avr': "Please output the indices of the images list, starting from 0. For example: [], or [0, 3], or [1, 4, 9]."
    },

    'VAR': {
        'prompt_var': "Please output the indices of the wavs list, starting from 0. For example: [], or [0, 3], or [1, 4, 9]."
    },

    'AVC': {

    },

    'AVLG': {
        'prompt_avlg': prompt_avlg,
    },

    'AVQA': {
        'avqa_cls_list': avqa_cls_list,
        'avqa_options_list_is': ['yes', 'no', 'not sure'],
    },

    'AVSQA': {
        'avsqa_options_list_object': ['cube', 'pyramid', 'cone', 'sphere', 'no availabel option', 'not sure'],
        'avsqa_options_list_color': ['red', 'blue', 'white', 'black', 'gray', 'green', 'no availabel option', 'not sure'],
        'prompt_avsqa': "You may choose multiple options; separated by semicolons. Your answer should be enclosed within ##, for example: #your_ans#."
    }
}
