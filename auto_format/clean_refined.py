"""
Clean refined outputs: remove ```json and ``` markers from predict fields.
Modifies files in-place.

Usage: python clean_refined.py
"""
import glob
import json
import os

REFINED_DIR = '../eval/user_outputs_refined'


def clean_predict(text):
    if not isinstance(text, str):
        return text
    text = text.replace('```json', '').replace('```', '').strip()
    return text


def process_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changed = 0
    for entry in data:
        old = entry.get('predict')
        if isinstance(old, str) and ('```' in old):
            entry['predict'] = clean_predict(old)
            changed += 1

    if changed > 0:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    return len(data), changed


if __name__ == '__main__':
    json_files = sorted(glob.glob(f'{REFINED_DIR}/*/tasks/*.json'))
    for jf in json_files:
        task = os.path.basename(jf).replace('.json', '')
        model = jf.split('/')[-3]
        total, changed = process_file(jf)
        print(f'{model}/{task}: {changed}/{total} cleaned')
