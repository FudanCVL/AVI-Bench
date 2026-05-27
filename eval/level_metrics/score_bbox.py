import ast
import re
import numpy as np
from sklearn.metrics import f1_score
from . import utils

def get_semantic_type(label: str) -> str:
    """
    Extract semantic category. e.g. 'person_1' -> 'person'; 'violin' -> 'violin'
    """
    if '_' in label:
        parts = label.rsplit('_', 1)
        if len(parts) == 2 and re.match(r'^\d+$', parts[1]):
            return parts[0].lower()
    return label.lower()

def get_bbox(bbox_str):
    if isinstance(bbox_str, str):
        try:
            bbox_str = ast.literal_eval(bbox_str)
        except:
            return None
    try:
        _bbox = [float(b) for b in bbox_str]
        if len(_bbox) != 4:
            return None
    except:
        return None
    return _bbox

def eval_avl(data_json_path, pred_json_path):
    labels, preds, _ = utils.parse_data_and_pred(data_json_path, pred_json_path, clean_symbol=False)

    all_videos_iou_list = []
    all_semantic_score_list = []
    all_instance_error_list = []

    for data_id in labels:
        _true_output = labels[data_id]

        try:
            _pred = ast.literal_eval(preds[data_id])
            assert isinstance(_pred, dict) and isinstance(_true_output, dict)
        except Exception as e:
            print(f"[Warning] Failed to parse prediction for {data_id}: {e}")
            all_videos_iou_list.append(0)
            all_semantic_score_list.append(0)
            all_instance_error_list.append(0)
            continue

        # Read GT bboxes and original image dimensions
        try:
            # print(_true_output)
            qa = _true_output
            true_bboxes = qa["bbox"]
            orig_w, orig_h = qa["original_wh"]
        except Exception as e:
            print(f"[Warning] Invalid label format in {data_id}: {e}")
            all_videos_iou_list.append(0)
            all_semantic_score_list.append(0)
            all_instance_error_list.append(0)
            continue

        instance_map = {}
        used_pred_keys = set()
        video_iou = 0

        for true_key, true_bbox in true_bboxes.items():
            max_iou = 0
            best_pred_key = None
            true_sem = get_semantic_type(true_key)

            true_bbox = [true_bbox[0], true_bbox[1], true_bbox[0]+true_bbox[2], true_bbox[1]+true_bbox[3]]

            for pred_key, pred_bbox_raw in _pred.items():
                pred_sem = get_semantic_type(pred_key)
                if pred_sem != true_sem or pred_key in used_pred_keys:
                    continue

                pred_bbox = get_bbox(pred_bbox_raw)
                if pred_bbox is None:
                    continue

                # Handle non-normalized predictions: prompt asks for [0,1] but
                # models often emit 0-1000-scaled or absolute pixel coords.
                m = max(abs(v) for v in pred_bbox)
                if m > 1.5 and m <= 1001:
                    # 0-1000 scaled → renormalize
                    pred_bbox = [v / 1000.0 for v in pred_bbox]
                    m = max(abs(v) for v in pred_bbox)

                x1, y1, x2, y2 = pred_bbox
                if m > 1.5:
                    # Looks like absolute pixel coords — skip rescaling.
                    pred_bbox_scaled = [x1, y1, x2, y2]
                else:
                    # Normalized [0,1] → scale back to image pixel dims
                    pred_bbox_scaled = [x1 * orig_w, y1 * orig_h, x2 * orig_w, y2 * orig_h]

                iou = utils.compute_iou(pred_bbox_scaled, true_bbox)
                if iou > max_iou:
                    max_iou = iou
                    best_pred_key = pred_key

            if max_iou > 0 and best_pred_key:
                instance_map[true_key] = best_pred_key
                used_pred_keys.add(best_pred_key)
                video_iou += max_iou

        matched_count = len(instance_map)
        # if matched_count > 0:
        #     video_iou /= matched_count
        video_iou /= (len(true_bboxes) + 0.00001)
        all_videos_iou_list.append(video_iou)

        # Instance error
        instance_err = len(true_bboxes) - matched_count
        all_instance_error_list.append(instance_err)

        # Semantic F1
        true_semantics = set(get_semantic_type(k) for k in true_bboxes.keys())
        pred_semantics = set(get_semantic_type(k) for k in _pred.keys())

        all_labels = list(true_semantics.union(pred_semantics))
        y_true = [1 if lbl in true_semantics else 0 for lbl in all_labels]
        y_pred = [1 if lbl in pred_semantics else 0 for lbl in all_labels]

        semantic_f1 = f1_score(y_true, y_pred, zero_division=0)
        all_semantic_score_list.append(semantic_f1)

    # Final aggregation
    final_miou = float(np.mean(all_videos_iou_list))
    final_semantic_score = float(np.mean(all_semantic_score_list))

    mse = np.mean(np.square(all_instance_error_list))
    rmse = np.sqrt(mse)
    final_instance_score = utils.rmse_to_score(rmse, k=1, b=0)

    if final_semantic_score == 0:
        final_instance_score = 0.0

    # final_score = 0.5 * final_miou + 0.3 * final_semantic_score + 0.2 * final_instance_score
    final_score = 0.7 * final_miou + 0.3 * final_instance_score
    
    res = {
        'miou': round(final_miou, 5),
        # 'semantic_f1': round(final_semantic_score, 5),
        'instance_score': round(final_instance_score, 5),
        'final_score': round(final_score, 5),
    }
    print(res)
    return res
