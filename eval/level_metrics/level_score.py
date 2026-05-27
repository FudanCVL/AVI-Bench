import json
import ast
import re
import numpy as np
from sklearn.metrics import f1_score, recall_score
from sympy import true
from . import test_cider
from sklearn.metrics import average_precision_score
from . import caption_scores
from . import score_bbox
from . import utils
from . import agent_eval_formatting

from pycocoevalcap.cider.cider import Cider

eval_avl = score_bbox.eval_avl

def eval_avsqa(data_json_path, pred_json_path, double_confirm=True):
    """ eval the full dict: AVSQA """
    # print('>>> eval')
    labels, preds, options = utils.parse_data_and_pred(data_json_path, pred_json_path, clean_symbol=False)
    # print(labels)

    score_dict = {}
    for idx, (data_id, data_label) in enumerate(labels.items()):
        # print('>>>', idx, data_id)
        data_pred = f'{preds[data_id]}'
        data_label = f'{data_label}'
        data_options = options[data_id]

        # Case-insensitive comparison: GT is always lowercase ('yes', 'cube',
        # 'pyramid' ...) but refined predictions often capitalize ('**Yes**',
        # '**Pyramid**'). Without this, 81 percent of the pre_ "Can you hear
        # any sound?" predictions would be marked wrong purely on case
        # mismatch, zeroing all corresponding formal scores via double-confirm
        # and crashing the AVSQA score (e.g. 18% formal accuracy -> 2%).
        data_label = data_label.lower().strip().split(';')
        data_pred = data_pred.replace('*', '').replace('#', '').lower().strip().split(';')
        data_label = [s.strip() for s in data_label]
        data_pred = [s.strip() for s in data_pred]

        data_label = sorted(data_label)
        data_pred = sorted(data_pred)

        # print('>>> data label:', data_label)
        # print('>>> data pred:', data_pred)
        # input()

        if data_pred == data_label:
            full_match_score = 1
        else:
            full_match_score = 0
        if full_match_score != 0:
            # print(f'{data_id}: {data_label} - {data_pred} - {full_match_score}')
            # input()
            ...
        if 'id=pre_' in data_id:  # pre_ questions placed after the formal questions.
            if full_match_score == 0 and double_confirm:
                # New key format `task=...#id=...#pos=...` makes a literal
                # replace miss because formal/pre share id but differ in pos.
                # Match the formal entry by id (drop the pre_ prefix), find
                # the corresponding key already in score_dict, and zero it.
                pre_id = data_id.split('#id=')[1].split('#')[0]
                formal_id = pre_id[len('pre_'):]
                marker = f'#id={formal_id}#'
                for k in list(score_dict.keys()):
                    if marker in k:
                        score_dict[k] = 0
                        break
        else:
            score_dict[data_id] = full_match_score  # only save the formal question answer.

    # get total acc.
    # print(score_dict)
    # input()
    acc = sum(score_dict.values()) / len(score_dict)
    return round(acc, 5)

def get_full_match_acc(pred: str, label: str):
    """ get answer for one data sample. """
    assert isinstance(pred, str), f'Pred shoud be str type: {type(pred)}'
    assert isinstance(label, str), f'Label shoud be str type: {type(label)}'

    if pred == label:
        return 1

    if label.isdigit():
        digit_in_str = utils.extract_first_number(pred)
        if f'{digit_in_str}' == label:
            return 1
    
    return 0


def eval_full_match_acc(data_json_path, pred_json_path, double_confirm=True):
    """ eval the full dict: sensation/perception/reasoning tasks """
    labels, preds, options = utils.parse_data_and_pred(data_json_path, pred_json_path, clean_symbol=True)

    # Find invalid pre_ entries (question.text or GT is None) and skip their
    # double-confirm penalty. The VSQA_I "common" subtask in the released
    # dataset has 147 such empty pre_ slots, which would otherwise zero out
    # every correct formal answer they pair with.
    invalid_pre_ids = set()
    raw_data = json.load(open(data_json_path, 'r', encoding='utf-8'))
    for d in raw_data:
        eid = str(d.get('id', ''))
        if not eid.startswith('pre_'): continue
        q_text = d.get('input', {}).get('question', {}).get('text')
        gt_ans = d.get('output', {}).get('question_answer')
        if q_text is None or gt_ans is None:
            invalid_pre_ids.add(eid)

    score_dict = {}
    for idx, (data_id, data_label) in enumerate(labels.items()):
        # Skip empty pre_ entries entirely (do not enter score_dict, do not
        # affect double-confirm).
        pre_id = data_id.split('#id=')[1].split('#')[0] if '#id=' in data_id else ''
        if pre_id in invalid_pre_ids:
            continue
        # print('>>>', idx, data_id)
        data_pred = f'{preds[data_id]}'
        data_label = f'{data_label}'
        data_options = options[data_id]

        # process input string  
        # print(data_options)
        if data_options is not None:
            res = utils.find_ordered_matches(data_options, data_pred)
            if res is not None:
                if len(res) > 0:
                    data_pred = res[0]

        
        full_match_score = get_full_match_acc(data_pred, data_label)
        if full_match_score != 0:
            # print(f'{data_id}: {data_label} - {data_pred} - {full_match_score}')
            # input()
            ...
        if 'id=pre_' in data_id:  # pre_ questions placed after the formal questions.
            if full_match_score == 0 and double_confirm:
                # New key format `task=...#id=...#pos=...` makes a literal
                # replace miss because formal/pre share id but differ in pos.
                # Match the formal entry by id (drop the pre_ prefix), find
                # the corresponding key already in score_dict, and zero it.
                pre_id = data_id.split('#id=')[1].split('#')[0]
                formal_id = pre_id[len('pre_'):]
                marker = f'#id={formal_id}#'
                for k in list(score_dict.keys()):
                    if marker in k:
                        score_dict[k] = 0
                        break
        else:
            score_dict[data_id] = full_match_score  # only save the formal question answer.

    # get total acc.
    # print(score_dict)
    # input()
    acc = sum(score_dict.values()) / len(score_dict)
    return round(acc, 5)


def eval_multi_instance_cls_and_count(data_json_path, pred_json_path, task_name):
    """ eval full dict: AMIC/VMIC """
    assert task_name.lower() in ['amic', 'vmic']
    labels, preds, options = utils.parse_data_and_pred(data_json_path, pred_json_path, clean_symbol=False)

    semantic_scores = []
    absolute_errors = []

    # semantic score
    for data_id in labels:
        # preds[data_id] = json.loads('{"tuba": "1", "piano": "1"}')  # TODO: pseudo code
        # print('>>>', preds[data_id])
        assert isinstance(preds[data_id], str), type(preds[data_id])
        # Strip leaked "answer=" prefix from refine output before JSON parse.
        s = preds[data_id].lstrip()
        if s.lower().startswith('answer='):
            s = s.split('=', 1)[1].lstrip()
        preds[data_id] = s.replace("'", '"')
        mk = 0.3 if task_name.lower() == 'amic' else 0.3
        tau = 7 if task_name.lower() == 'amic' else 12
        if len(preds[data_id]) >= 300:
            # semantic_scores.append(0)
            continue
        try:
            preds[data_id] = json.loads(preds[data_id])
            pred_cls = preds[data_id].keys()
            true_cls = labels[data_id].keys()

            if task_name.lower() == 'amic':
                all_labels = set(preds[data_id].keys()).union(set(labels[data_id].keys()))
            elif task_name.lower() == 'vmic':
                all_labels = set(labels[data_id].keys())  # recall, different with audio

            y_true = [1 if label in true_cls else 0 for label in all_labels]
            y_pred = [1 if label in pred_cls else 0 for label in all_labels]

            if task_name.lower() == 'amic':
                semantic_scores.append(f1_score(y_true, y_pred))
            elif task_name.lower() == 'vmic':
                semantic_scores.append(recall_score(y_true, y_pred))
        except:
            semantic_scores.append(0)

    # recognition_score (counting) 
    for k_label in labels:  
    # for (k_label, k_pred) in zip(labels, preds):
        label = labels[k_label]
        pred = preds[k_label]
        # label, pred = labels[k_label], preds[k_pred]
        # pred = json.loads('{"tree": "1", "dog": "1", "car": "2"}')  # TODO: pseudo code
        # print(label, pred)
        if len(f'{pred}') >= 300:
            continue
        _label_abs_list = []
        try:
            pred = json.loads(f'{pred}'.replace("'", '"'))
            # print('===>', label, pred)
            
            for k in label:
                # print('>>> lab:', k, label[k])
                if k in pred:
                    abs_err = abs(int(pred[k]) - int(label[k]))
                    if task_name.lower() == 'vmic' and int(pred[k]) >= 10 and int(label[k]) >= 10:  # noisy labels for image
                        abs_err = 0
                else:
                    # abs_err = int(label[k])  # Not predicted, use label count as error
                    abs_err = tau  # Not predicted, use tau as default error
                _label_abs_list.append(abs_err)
                # print(">>>>>> pred:", pred[k], abs_err)
        except Exception as err:
            print('>>> err:', err, ' | ', pred)
            for k in label:
                abs_err = int(label[k])
                _label_abs_list.append(abs_err)

        label_abs = np.mean(_label_abs_list).__float__()
        label_abs = min(label_abs, 20)
        absolute_errors.append(label_abs)

    # Compute semantic score
    semantic_score = np.mean(semantic_scores)
    # Compute MSE & RMSE
    # print(absolute_errors)
    mse = np.mean(np.square(absolute_errors))
    rmse = np.sqrt(mse)
    print('>>> rmse:', rmse)
    counting_score = utils.rmse_to_score(rmse, k=mk, b=0)

    if semantic_score == 0:
        counting_score = 0
    mic_score = (semantic_score + counting_score) / 2  # multi-instance classification and counting

    print(f'> mic_score: {mic_score:.5f} | semantic: {semantic_score:.5f} | counting: {counting_score:.5f}')
    mic_score, semantic_score, counting_score = round(float(mic_score), 5), round(float(semantic_score), 5), round(float(counting_score), 5)
    return mic_score, semantic_score, counting_score

def eval_caption_with_references(data_json_path, pred_json_path):
    """Score AVC predictions using FENSE.

    FENSE (Zhou et al., ICASSP 2022) combines sentence-BERT similarity with a
    fluency error detector. It is the metric used in the camera-ready Obs5
    revision (W4 reviewer request), replacing the older
    METEOR/ROUGE-L/CIDEr/SBERT n-gram average that unfairly penalized verbose
    closed-source captions.

    Returns a dict with the corpus-level FENSE, plus its two components
    (sbert_sim, fer) for diagnostic purposes. The headline `average` field is
    the FENSE score, so downstream tooling that reads `average` keeps working.
    """
    import os
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    # aac_metrics bug-workaround: some transformers dev versions have
    # non-PEP440 version strings ("4.52.0.dev0") that crash the loader's
    # version check. Force the modern loader code path on failure.
    import importlib as _importlib
    _fer = _importlib.import_module("aac_metrics.functional.fer")
    _orig_use_new = getattr(_fer, "_use_new_echecker_loading", None)
    if _orig_use_new is not None:
        def _patched_use_new():
            try:
                return _orig_use_new()
            except ValueError:
                return True
        _fer._use_new_echecker_loading = _patched_use_new

    from aac_metrics.functional import fense as fense_fn

    labels, preds, options = utils.parse_data_and_pred(data_json_path, pred_json_path, clean_symbol=False)

    candidates = []
    mult_refs = []
    for data_id in labels:
        refs = labels[data_id]
        pred = preds[data_id]
        if pred is None or pred == "":
            continue
        # Normalize refs into list[str]
        if isinstance(refs, list):
            ref_strs = [str(r) for r in refs if r]
        else:
            ref_strs = [str(refs)]
        if not ref_strs:
            continue
        candidates.append(str(pred))
        mult_refs.append(ref_strs)

    if not candidates:
        return {"fense": 0.0, "sbert_sim": 0.0, "fer": 0.0, "n_samples": 0, "average": 0.0}

    corpus, _sample = fense_fn(candidates, mult_refs)
    fense_score = corpus["fense"].item()
    sbert = corpus["sbert_sim"].item()
    fer_score = corpus["fer"].item()

    return {
        "fense": round(fense_score, 5),
        "sbert_sim": round(sbert, 5),
        "fer": round(fer_score, 5),
        "n_samples": len(candidates),
        "average": round(fense_score, 5),  # headline score is FENSE
    }
    
def set_f1(pred_set, true_set):
    pred_set, true_set = set(pred_set), set(true_set)
    if not pred_set and not true_set:
        return 1.0
    if not pred_set or not true_set:
        return 0.0
    precision = len(pred_set & true_set) / len(pred_set)
    recall = len(pred_set & true_set) / len(true_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)

def eval_retrieval(data_json_path, pred_json_path):
    labels, preds, options = utils.parse_data_and_pred(data_json_path, pred_json_path, clean_symbol=True)

    f1_scores = []
    recall_1_list = []
    recall_3_list = []
    ap_list = []
    full_match_list = []

    confidence_list = []
    pred_list = []
    true_list = []
    for idx, data_id in enumerate(labels):
        # print('>>> idx', idx, end='\r')
        _true = labels[data_id]
        # print(preds[data_id])
        og_pred = _pred = preds[data_id]
        if _pred is not None:
            _pred = _pred.replace('\n', ' ').split(' ')
        else:
            _pred = []

        # print(_pred)
        # input()
        _pred = sorted([int(p) for p in _pred if p.isdigit()])
        # print('> p:', idx, _pred,  _true)
        _pred = list(set(_pred))
        f1_scores.append(set_f1(_pred, _true))

        if _pred not in pred_list:
            pred_list.append(_pred)
        if _true not in true_list:
            true_list.append(_true)

        confidence = 0.3 if len(_pred) > 6 else 1
        confidence_list.append(confidence)

        # Recall@1
        hit_at_1 = any(p in _true for p in _pred[:1])
        recall_1_list.append(1.0 if hit_at_1 else 0.0)

        # Recall@3
        hit_at_3 = any(p in _true for p in _pred[:3])
        recall_3_list.append(1.0 if hit_at_3 else 0.0)

        # AP (with binary relevance and position weights)
        relevance = [1 if p in _true else 0 for p in _pred]
        if any(relevance):
            scores = [1.0 / (i + 1) for i in range(len(relevance))]  # reciprocal rank as dummy score
            ap = average_precision_score(relevance, scores)
            ap_list.append(ap)
        else:
            ap_list.append(0.0)

    repeat_rate_pred = (len(labels) - len(pred_list)) / len(labels)

    tau = 0.8
    repeat_rate_pred = max(tau, repeat_rate_pred)
    repeat_pred_penalty = 1 - (repeat_rate_pred - tau)  # Higher is better, capped at 1

    
    confidence_overall = np.mean(confidence_list)
    # confidence_overall = 1
    r1 = round(np.mean(recall_1_list) * confidence_overall * repeat_pred_penalty, 5)
    r3 = round(np.mean(recall_3_list) * confidence_overall * repeat_pred_penalty, 5)
    f1 = round(np.mean(f1_scores) * confidence_overall * repeat_pred_penalty, 5)

    avg = ((r1 + r3) /2 + f1) / 2
    res = {
        "Recall@1": r1,
        "Recall@3": r3,
        "F1_score": f1,
        "Average": avg,
    }

    # print('>>> retrieval:', res)
    print('- conf:', confidence_overall, '| repeat_penalty:', repeat_pred_penalty)
    return res

def eval_avlg(data_json_path, pred_json_path):
    labels, preds, options = utils.parse_data_and_pred(data_json_path, pred_json_path, clean_symbol=False)

    iou_list = []
    for idx, data_id in enumerate(labels):
        # print('>>> idx', idx, data_id, end='\r')
        _true = labels[data_id]

        _pred = preds[data_id]
        # print(_pred)
        if _pred is not None:
            _pred = _pred.replace('```json', '').replace('```', '').strip()
        else:
            _pred = "{'frame_0': []}"

        # Parse prediction string to dict
        try:
            pred_dict = ast.literal_eval(_pred)
        except Exception as e:
            print(f"Error parsing prediction for {data_id}: {e} \n_pred: {_pred}")
            pred_dict = {}
        # Guard against non-dict outputs (e.g., LLM returned a bare list of boxes).
        if not isinstance(pred_dict, dict):
            pred_dict = {}

        # Get GT dimensions and bbox
        # print('>>> true:', _true)
        original_wh = _true["original_wh"]
        w, h = original_wh
        true_bbox_dict = _true["bbox"]

        iou_score = 0
        for frame_key, true_box in true_bbox_dict.items():
            pred_box_norm = pred_dict.get(frame_key, None)

            if true_box is None:
                if pred_box_norm is None:
                    iou = 1
                elif pred_box_norm is not None:
                    iou = 0
            elif pred_box_norm is None:
                iou = 0
            else:
                try:
                    # Denormalize [x1, y1, x2, y2] to original dimensions
                    x1 = pred_box_norm[0] * w
                    y1 = pred_box_norm[1] * h
                    x2 = pred_box_norm[2] * w
                    y2 = pred_box_norm[3] * h
                    pred_box = [x1, y1, x2, y2]
                    # pred_box = true_box
                    true_box = [true_box[0], true_box[1], true_box[0]+true_box[2], true_box[1]+true_box[3]]  # to: [x1, y1, x2, y2]
                    iou = utils.compute_iou(true_box, pred_box)
                except Exception as err:
                    print(f">>> compute_iou error for {frame_key}: {err} | {pred_box_norm} | {true_box}")
                    iou = 0
            iou_score += iou

        video_iou_score = iou_score / len(true_bbox_dict)
        iou_list.append(video_iou_score)

    iou = np.mean(iou_list).__float__()
    return round(iou, 5)
