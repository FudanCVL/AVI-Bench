"""
Evaluate refined predictions against ground truth labels.
Auto-detects models from user_outputs_refined/ directory.

Usage:
    cd <repo>/eval
    python eval.py                          # evaluate all models
    python eval.py --models gemini-2.5-pro  # evaluate specific model
"""
import json
import os
import argparse

import nltk
nltk.download('wordnet', quiet=True)

import level_metrics

REFINED_DIR = os.environ.get('REFINED_DIR', './user_outputs_refined')
DATA_ROOT = os.environ.get('DATA_ROOT', '../data/levels')
EVAL_OUTPUT_DIR = os.environ.get('EVAL_OUTPUT_DIR', './eval_outputs')

# Task definitions: (task_name, category, eval_function_key)
TASK_DEFS = [
    # Sensation
    ('ASQA',   'sensation',  'full_match'),
    ('VSQA_I', 'sensation',  'full_match'),
    ('VSQA_V', 'sensation',  'full_match'),
    ('AVSQA',  'sensation',  'avsqa'),
    # Perception
    ('AMIC',   'perception', 'mic'),
    ('VMIC',   'perception', 'mic'),
    ('AVL',    'perception', 'avl'),
    ('AVM',    'perception', 'full_match'),
    # Understand
    ('AVR',    'understand', 'retrieval'),
    ('VAR',    'understand', 'retrieval'),
    ('AVC',    'understand', 'caption'),
    # Reasoning
    ('AVH',    'reasoning',  'full_match'),
    ('VAH',    'reasoning',  'full_match'),
    ('AVQA',   'reasoning',  'full_match'),
    ('AVLG',   'reasoning',  'avlg'),
]


def eval_task(task_name, category, eval_key, data_root, pred_dir):
    """Evaluate a single task. Returns score dict or None on failure."""
    data_json = os.path.join(data_root, category, task_name, 'data.json')
    pred_json = os.path.join(pred_dir, f'{task_name}.json')

    if not os.path.exists(pred_json):
        return None, f'pred not found: {pred_json}'
    if not os.path.exists(data_json):
        return None, f'data not found: {data_json}'

    if eval_key == 'full_match':
        score = level_metrics.level_score.eval_full_match_acc(data_json, pred_json)
        return score, None

    elif eval_key == 'avsqa':
        score = level_metrics.level_score.eval_avsqa(data_json, pred_json)
        return score, None

    elif eval_key == 'mic':
        average, semantic, instance = level_metrics.level_score.eval_multi_instance_cls_and_count(
            data_json, pred_json, task_name=task_name.lower())
        return {'Semantic': semantic, 'Instance': instance, 'Average': average}, None

    elif eval_key == 'avl':
        res = level_metrics.level_score.eval_avl(data_json, pred_json)
        return {'mIoU': res['miou'], 'Instance': res['instance_score'], 'Average': res['final_score']}, None

    elif eval_key == 'retrieval':
        score = level_metrics.level_score.eval_retrieval(data_json, pred_json)
        return score, None

    elif eval_key == 'caption':
        # AVC: FENSE metric (returns dict with fense/sbert_sim/fer/n_samples/average)
        return level_metrics.level_score.eval_caption_with_references(data_json, pred_json), None

    elif eval_key == 'avlg':
        score = level_metrics.level_score.eval_avlg(data_json, pred_json)
        return score, None

    return None, f'unknown eval_key: {eval_key}'


def evaluate_model(model_name):
    pred_dir = os.path.join(REFINED_DIR, model_name, 'tasks')
    if not os.path.exists(pred_dir):
        print(f'>>> pred dir not found: {pred_dir}')
        return

    print(f'\n{"="*70}')
    print(f'  Model: {model_name}')
    print(f'{"="*70}')

    levels_score = {
        'sensation': {},
        'perception': {},
        'understand': {},
        'reasoning': {},
    }

    for task_name, category, eval_key in TASK_DEFS:
        try:
            score, err = eval_task(task_name, category, eval_key, DATA_ROOT, pred_dir)
            if err:
                print(f'  {task_name:8s} SKIP  ({err})')
            else:
                levels_score[category][task_name.lower()] = score
                print(f'  {task_name:8s} OK    {score}')
        except Exception as e:
            print(f'  {task_name:8s} ERROR {e}')

    # Combine VSQA_I + VSQA_V into a single VSQA score (paper treats them as one task).
    # Pool the data.json / predictions and run full_match_acc once on the merged 1200 samples.
    try:
        import tempfile, os as _os
        di = json.load(open(_os.path.join(DATA_ROOT, 'sensation/VSQA_I/data.json')))
        dv = json.load(open(_os.path.join(DATA_ROOT, 'sensation/VSQA_V/data.json')))
        pi = json.load(open(_os.path.join(pred_dir, 'VSQA_I.json')))
        pv = json.load(open(_os.path.join(pred_dir, 'VSQA_V.json')))
        # Prefix ids with task prefix to avoid id collisions in the merged set.
        # IMPORTANT: keep `pre_` at the start so double-confirm logic in
        # eval_full_match_acc still detects pre-question entries.
        def _tag(eid, tag):
            s = str(eid)
            return f'pre_{tag}-{s[4:]}' if s.startswith('pre_') else f'{tag}-{s}'
        for d in di: d['id'] = _tag(d['id'], 'I')
        for d in dv: d['id'] = _tag(d['id'], 'V')
        for p in pi:
            if p: p['id'] = _tag(p['id'], 'I')
        for p in pv:
            if p: p['id'] = _tag(p['id'], 'V')
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f_d, \
             tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f_p:
            json.dump(di + dv, f_d)
            json.dump(pi + pv, f_p)
            f_d.flush(); f_p.flush()
            vsqa_score = level_metrics.level_score.eval_full_match_acc(f_d.name, f_p.name)
        sens = levels_score.get('sensation', {})
        sens['vsqa'] = vsqa_score
        # Drop per-half scores so output cleanly presents VSQA as one task.
        sens.pop('vsqa_i', None)
        sens.pop('vsqa_v', None)
        print(f'  VSQA     OK    {vsqa_score}  (1200 samples pooled VSQA_I + VSQA_V)')
    except Exception as e:
        print(f'  VSQA combine SKIP: {e}')

    # Save results
    os.makedirs(EVAL_OUTPUT_DIR, exist_ok=True)
    save_path = os.path.join(EVAL_OUTPUT_DIR, f'{model_name}.json')
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(levels_score, f, indent=4, ensure_ascii=False)
    print(f'\n>>> Results saved to {save_path}')

    return levels_score


def main():
    parser = argparse.ArgumentParser(description='AVIBench Evaluation')
    parser.add_argument('--models', nargs='+', default=None,
                        help='Model names to evaluate. If not set, evaluate all models in refined dir.')
    args = parser.parse_args()

    if args.models:
        model_list = args.models
    else:
        model_list = sorted(os.listdir(REFINED_DIR))

    for model_name in model_list:
        evaluate_model(model_name)


if __name__ == '__main__':
    main()
