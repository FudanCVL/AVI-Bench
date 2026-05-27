import os
import json
import numpy as np
import re
import ast

from . import data_utils

todo_clean = [
    '<|endoftext|>',
]

def string_cleaning(_str, clean_symbol):
    for pat in todo_clean:
        _str = _str.replace(pat, '')
    if clean_symbol:
        _str = re.sub(r'[^\w\s]', '', _str.lower())
    return _str


def parse_data_and_pred(data_json_path, pred_json_path, clean_symbol):
    """Pair GT with predictions by position in the list.

    NOTE: Some tasks (e.g. AVQA) deliberately reuse the same `id` across
    different questions about the same media. The old (`task#id`) keying
    collided in those cases and silently dropped half the pairs, which
    corrupted scoring. We now align by array position and use
    `task#id#pos` as the dict key for downstream lookups.
    """
    assert os.path.exists(data_json_path), f'Not found: {data_json_path}'
    assert os.path.exists(pred_json_path), f'Not found: {pred_json_path}'

    data = json.load(open(data_json_path, 'r', encoding='utf-8'))
    preds = json.load(open(pred_json_path, 'r', encoding='utf-8'))

    n = min(len(data), len(preds))
    if len(data) != len(preds):
        print(f'>>> partial preds: data={len(data)}, pred={len(preds)} (scoring first {n} positions)')

    gt_labels = {}
    options = {}
    pred_dicts = {}
    for i in range(n):
        _d = data[i]
        _p = preds[i]
        # Skip slots where prediction is missing (None placeholder or null predict)
        if _p is None:
            continue
        if _p.get('predict') is None:
            continue
        key = f'task={_d["task"]}#id={_d["id"]}#pos={i}'
        gt_labels[key] = _d['output']['question_answer']
        options[key] = data_utils.get_real_options_or_classes(_d, with_pmp=False)
        pred_dicts[key] = string_cleaning(_p['predict'], clean_symbol)

    return gt_labels, pred_dicts, options


def extract_first_number(text):
    match = re.search(r'\d+', text)
    if match:
        return match.group(0)
    return None



# def rmse_to_score(rmse, k):
#     """Convert RMSE to score (0~1, higher is better)"""
#     assert rmse >= 0, rmse
#     x = k * rmse
#     sigmoid = 1 / (1 + np.exp(-(x-0)))  # Sigmoid compression
#     score = 1 - sigmoid   # Complement
#     return score

def rmse_to_score(rmse, k=0.3, b=0):
    """Convert RMSE to score (0~1, higher is better) using tanh."""
    try:
        assert rmse >= 0, rmse
    except Exception as err:
        return 0
    x = k * rmse
    score = np.tanh(x + b)  # tanh compression
    score = 1 - score  # Invert so higher score = better
    return score

# x = rmse_to_score(4, k=0.06)
# print(x)



def extract_list_from_string(input_string):
    # Extract bracket content using regex
    match = re.search(r'\[(.*?)\]', input_string)
    if match:
        list_content = match.group(1)
        return ast.literal_eval(f'[{list_content}]')
    return []


def f1_score(pred, true):
    pred_set = set(pred)
    true_set = set(true)
    
    TP = len(pred_set & true_set)  # True Positives
    FP = len(pred_set - true_set)   # False Positives
    FN = len(true_set - pred_set)   # False Negatives

    if TP == 0:
        return 0.0  # Avoid division by zero
    
    precision = TP / (TP + FP)
    recall = TP / (TP + FN)

    f1 = 2 * (precision * recall) / (precision + recall)
    return f1

def compute_iou(boxA, boxB):
    """
    Compute IoU of two bboxes in [x_min, y_min, x_max, y_max] format.
    """
    # Intersection coordinates
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    # Intersection area
    inter_width = max(0, xB - xA)
    inter_height = max(0, yB - yA)
    inter_area = inter_width * inter_height

    # Area of each box
    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    # IoU
    union_area = areaA + areaB - inter_area
    if union_area == 0:
        return 0.0

    iou = inter_area / float(union_area)
    return iou

# # Example:
# label = [295.0, 205.0, 928.0, 250.0]
# pred = [0.0, 0.0, 1280.0, 360.0]

# print("IoU =", compute_iou(label, pred))

def compute_iou_wh(bbox1, bbox2):
    """ input: bbox1: pred; bbox: true """
    # Unpack bounding boxes
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    # Convert to [x_min, y_min, x_max, y_max]
    box1 = [x1, y1, x1 + w1, y1 + h1]
    box2 = [x2, y2, x2 + w2, y2 + h2]

    # Intersection coordinates
    inter_x_min = max(box1[0], box2[0])
    inter_y_min = max(box1[1], box2[1])
    inter_x_max = min(box1[2], box2[2])
    inter_y_max = min(box1[3], box2[3])

    # Intersection area
    inter_width = max(0, inter_x_max - inter_x_min)
    inter_height = max(0, inter_y_max - inter_y_min)
    inter_area = inter_width * inter_height

    # Area of each box
    area1 = w1 * h1
    area2 = w2 * h2

    # Union area
    union_area = area1 + area2 - inter_area

    # IoU
    iou = inter_area / union_area if union_area > 0 else 0

    return round(iou.__float__(), 7)


def extract_json_from_string(text):
    # Match outermost curly brace content
    pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
    matches = re.findall(pattern, text, re.DOTALL)

    if not matches:
        return None

    # Select the longest match (largest JSON)
    largest_json_str = max(matches, key=len)
    # print('>>> ', largest_json_str)

    try:
        # Validate JSON
        parsed_json = json.loads(largest_json_str)
        # print('>>> parsed:', parsed_json)
        return largest_json_str
    except json.JSONDecodeError:
        print('>>> invalid. returen None.')
        return None
    
def find_ordered_matches(keywords, long_str):
    # Remove punctuation and convert to lowercase
    cleaned_str = re.sub(r'[^\w\s]', '', long_str.lower())

    result = []
    for word in keywords:
        # Clean keyword the same way
        cleaned_word = re.sub(r'[^\w\s]', '', word.lower())
        # Use regex to ensure whole-word matching
        pattern = re.compile(r'\b' + re.escape(cleaned_word) + r'\b')
        match = pattern.search(cleaned_str)
        if match:
            result.append((match.start(), word))  # Keep original case

    result.sort()
    return [word for _, word in result]
