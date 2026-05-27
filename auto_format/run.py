import glob
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import utils
import agent_format
from definitions import TASK_TO_CATEGORY

from tqdm import tqdm

RES_DIR = os.environ.get('AUTO_FORMAT_RES_DIR', '../eval/user_outputs')
SAVE_RES_DIR = os.environ.get('AUTO_FORMAT_SAVE_DIR',
                              RES_DIR.replace('user_outputs', 'user_outputs_refined'))
DATA_ROOT = os.environ.get('DATA_ROOT', '../data/levels')
REFINE_CONCURRENCY = int(os.environ.get('REFINE_CONCURRENCY', 1))


def _parallel_refine(pred_list, build_prompt, postprocess=None, label=''):
    """Concurrently call the refine LLM for each item.

    build_prompt(idx, entry) -> str (the prompt to send), or None to skip.
    postprocess(raw_response) -> final string. Defaults to clean_json_output.
    """
    pp = postprocess if postprocess is not None else clean_json_output

    def work(idx):
        entry = pred_list[idx]
        prompt = build_prompt(idx, entry)
        if prompt is None:
            return idx, None, None
        try:
            raw = agent_format.get_response_from_llm_agent(prompt)
            return idx, pp(raw), None
        except Exception as e:
            return idx, None, e

    n = len(pred_list)
    if REFINE_CONCURRENCY <= 1:
        for i in range(n):
            idx, refined, err = work(i)
            if err is not None:
                print(f'>>> err at idx={idx}: {err}')
            elif refined is not None:
                pred_list[idx]['predict'] = refined
    else:
        with ThreadPoolExecutor(max_workers=REFINE_CONCURRENCY) as pool:
            futs = [pool.submit(work, i) for i in range(n)]
            with tqdm(total=n, desc=label or 'refine') as pbar:
                for f in as_completed(futs):
                    idx, refined, err = f.result()
                    if err is not None:
                        print(f'>>> err at idx={idx}: {err}')
                    elif refined is not None:
                        pred_list[idx]['predict'] = refined
                    pbar.update(1)


def remove_duplicates(source_data):
    """Deduplicate by (id, task, subtask) composite key to handle tasks with duplicate IDs."""
    unique_data = {}
    for entry in source_data:
        key = (entry['id'], entry.get('task', ''), entry.get('subtask', ''))
        unique_data[key] = entry
    return list(unique_data.values())


def clean_json_output(text):
    """Clean LLM output to extract JSON content."""
    if text is None:
        return ''
    text = text.replace('```json', '').replace('```', '')
    text = text.replace('\n', '').replace('\"', "'").replace('    ', '')
    text = text.replace('null', '[]')
    # Strip leaked "answer=" prefix from LLM refine output (gemini occasionally
    # leaks the QA-style answer label into MIC/retrieval outputs).
    s = text.lstrip()
    if s.lower().startswith('answer='):
        s = s.split('=', 1)[1].lstrip()
        text = s
    return text


# ======================== Task-specific refine prompts ========================

PROMPT_RETRIEVAL = """
Please convert the provided text into a specific dictionary format.
The format should consist a list of indices.
For example, if given the input ```python [0, 1, 3, 7, 8]```, which means the index selected, it should maintain that structure.
The output should always be in the form of a list with numeric values represented for selected indices, any non-numeric values should be removed.
Make sure to convert them into the specified format accurately.
Now, the provided text is: MODEL_MSG. Your refined output is: ```json
"""

PROMPT_AVLG = """
You are a helpful assistant dedicated to formatting outputs from other models according to specific guidelines.
### Requirements:
1. Convert the output into JSON format with the following structure:
```json
{
    "frame_0": [0.1, 0.11, 0.21, 0.14],
    "frame_1": [0.2, 0.3, 0.4, 0.12],
    ...
    "frame_9": [0.22, 0.31, 0.2, 0.11]
}
```
2. If a frame is missing a complete bounding box (e.g., `[0.22, 0.31, 0.2, `), set that frame's bounding box to `[]`. For example, change `'frame_5': [0.22, 0.31, 0.2,` to `'frame_5': []`.
3. If the bounding boxes contain invalid values (e.g., letters like in `[x_y, 010, xy, yy]`, `[x_1, y_1, w_1, h_1]`, or similar), set that frame's bounding box to `[]`. For instance, change `'frame_5': [x_4, y_4, w_4, h_4]` to `'frame_5': []`.
4. If the input contains more than 10 frames, remove any excess frames, ensuring only frames from `frame_0` to `frame_9` are included.
5. Ensure that the output includes frames from `frame_0` to `frame_9`, and that all bounding boxes contain only numeric values.
Now, the output content from the other model is: `MODEL_MSG`. Your refined output is: ```json
"""

PROMPT_AVL = """
You are a helpful assistant designed to format outputs from other models according to specific requirements.
### Requirements:
1. Convert the output into JSON format with the following structure:
    ```json
    {
        "banjo_1": "[0.1, 0.11, 0.21, 0.14]",
        "guitar_2": "[0.2, 0.3, 0.4, 0.12]",
        "guitar_3": "[0.22, 0.31, 0.2, 0.11]"
    }
```
2. Ensure that the output includes object category, corresponding instance id, and that the bounding boxes only contain numeric values.
Now, the output content from the other model is: `MODEL_MSG`. Your refined output is: ```json
"""

PROMPT_MIC = """
Please convert the provided text into a specific dictionary format.
The format should consist of objects as keys and their corresponding instance counts as values.
For example, if given the input ```json{"bird": "1", "man": "2"}```, it should maintain that structure.

If the content is in plain text, such as "a dog is barking, and two men are walking,"
extract the objects and count their occurrences to present them in the same dictionary format, e.g., ```json{"dog": "1", "man": "2"}```
The output should always be in the form of a JSON-like dictionary with string values representing counts.

Please also note thay the key should contain only one-word, i.e., if the key is "black dog" and "old woman", please convert as "dog" and "man".

Make sure to identify various objects in the text, and convert them into the specified format accurately.
Now, the provided text is: MODEL_MSG. Your refined output is: ```json
"""

PROMPT_QA = """
You are an excellent information extraction expert, helping me extract the actual answers represented from the cluttered outputs of a model cluster.
The content provided to you consists of three parts:
- The original information received by the model cluster, namely the question, enclosed with [>original_question] original question [original_question<].
- The responses from the model cluster to the original question, enclosed with [>original_responses] original_responses [original_responses<]; these responses are very verbose, containing reasoning, explanations, and answers, but we only need the final answer.
- A prompt regarding the content you are expected to output, enclosed with [>what_you_should_do] what_you_should_do [what_you_should_do<].
Now, I will provide you with the above information:
[>original_question] x_original_question [original_question<]
[>original_responses] x_original_responses [original_responses<]
[>what_you_should_do] x_what_you_should_do [what_you_should_do<]
If you cannot find the answer, you should response with "i dont know".
Note, please do not explain, just give the final answer enclosed with ** **, e.g., **the answer is ...**.
Now, please analysis the original question and original_responses, reference what_you_should_do, you can extract the correct answer=
"""


# ======================== Refine logic per task type ========================

def refine_retrieval(pred_list, model_name):
    """Refine VAR / AVR predictions."""
    def build(idx, _d):
        pred = _d['predict'] if _d['predict'] is not None else '[]'
        return PROMPT_RETRIEVAL.replace('MODEL_MSG', str(pred))
    _parallel_refine(pred_list, build, label=f'{model_name}/retrieval')


def refine_avlg(pred_list, model_name):
    """Refine AVLG predictions."""
    def build(idx, _d):
        pred = _d['predict'] if _d['predict'] is not None else '[]'
        return PROMPT_AVLG.replace('MODEL_MSG', str(pred))
    _parallel_refine(pred_list, build, label=f'{model_name}/avlg')


def refine_avl(pred_list, model_name):
    """Refine AVL predictions."""
    def build(idx, _d):
        pred = _d['predict'] if _d['predict'] is not None else '{}'
        return PROMPT_AVL.replace('MODEL_MSG', str(pred))
    _parallel_refine(pred_list, build, label=f'{model_name}/avl')


def refine_mic(pred_list, model_name):
    """Refine AMIC / VMIC predictions."""
    def build(idx, _d):
        pred = _d['predict'] if _d['predict'] is not None else '{}'
        return PROMPT_MIC.replace('MODEL_MSG', str(pred))
    _parallel_refine(pred_list, build, label=f'{model_name}/mic')


def refine_qa(pred_list, label_list, task_name, model_name):
    """Refine QA tasks (ASQA, VSQA_I, VSQA_V, AVSQA, AVQA). Aligned by array index."""
    def build(i, pred):
        label = label_list[i]
        original_question = utils.get_real_input(label)
        in_pmp = PROMPT_QA.replace('x_original_question', original_question)
        if label['task'] == 'ASQA':
            if label.get('subtask') == 'beats_counting':
                pmp2 = 'The answer should be a number, if the original answer is of English, convert it into a number. e.g., "because... the answer is four" -> "**4**". '
            else:
                pmp2 = 'Only remain the correct answer/option, remove all of other redundant words. e.g., "because... the first... the second... the answer is second." -> "**second**"'
        elif label['task'] in ['VSQA_I', 'VSQA_V', 'AVSQA']:
            pmp2 = 'If the question is about the quantity, the final answer should be a number, if the original answer is of English, convert it into a number. e.g., "because... the answer is four" -> "**4**". '
            pmp2 += 'Else, the final answer should be the selected option without any explain, e.g., "the left is small, the righ is big, so the answer is big" -> "**right**"'
        elif 'AVQA' in label['task']:
            pmp2 = 'If the question is about the quantity, the final answer should be a number, if the original answer is of English, convert it into a number. e.g., "because... the answer is four" -> "**4**". '
            pmp2 += 'Else, the final answer should be the selected option without any explain, e.g., "the left is small, the righ is big, so the answer is big" -> "**right**"'
        else:
            return None
        in_pmp = in_pmp.replace('x_what_you_should_do', pmp2)
        output_pred = pred['predict'] if pred['predict'] is not None else 'i dont know'
        return in_pmp.replace('x_original_responses', str(output_pred))

    # QA refine returns the raw text (no clean_json_output), so override postprocess.
    _parallel_refine(pred_list, build, postprocess=lambda x: x, label=f'{model_name}/{task_name}')


# ======================== Main refine function ========================

# Tasks that need no LLM refinement (simple yes/no or direct answers)
NO_REFINE_TASKS = {'AVM', 'AVC', 'AVH', 'VAH'}

# QA tasks that need answer extraction
QA_TASKS = {'ASQA', 'VSQA_I', 'VSQA_V', 'AVSQA', 'AVQA'}


def refine(model_name):
    model_eval_out = f'{RES_DIR}/{model_name}/tasks'
    print(f'\n{"="*60}')
    print(f'Model: {model_name}')
    print(f'Input:  {model_eval_out}')

    if not os.path.exists(model_eval_out):
        print(f'>>> not found: {model_eval_out}')
        return

    json_list = glob.glob(f'{model_eval_out}/*.json')

    for jf in sorted(json_list):
        task_name = os.path.basename(jf).replace('.json', '')
        category = TASK_TO_CATEGORY.get(task_name)
        if category is None:
            print(f'>>> skip unknown task: {task_name}')
            continue

        print(f'\n--- {task_name} ---')

        # Check save target
        save_tgt = f'{SAVE_RES_DIR}/{model_name}/tasks/{task_name}.json'
        if os.path.exists(save_tgt):
            print(f'>>> already refined, skip: {save_tgt}')
            continue

        # Load predictions (no deduplication — dataset may have duplicate IDs)
        with open(jf, 'r', encoding='utf-8') as rf:
            pred_list = json.load(rf)

        # Load labels
        label_json = f'{DATA_ROOT}/{category}/{task_name}/data.json'
        if not os.path.exists(label_json):
            print(f'>>> label not found: {label_json}')
            continue
        with open(label_json, 'r', encoding='utf-8') as rf:
            label_list = json.load(rf)

        # Verify count
        if len(label_list) != len(pred_list):
            print(f'>>> WARNING: label({len(label_list)}) != pred({len(pred_list)}), proceeding anyway')

        # Dispatch to task-specific refine logic
        if task_name in ('VAR', 'AVR'):
            refine_retrieval(pred_list, model_name)
        elif task_name == 'AVLG':
            refine_avlg(pred_list, model_name)
        elif task_name == 'AVL':
            refine_avl(pred_list, model_name)
        elif task_name in ('AMIC', 'VMIC'):
            refine_mic(pred_list, model_name)
        elif task_name in QA_TASKS:
            refine_qa(pred_list, label_list, task_name, model_name)
        elif task_name in NO_REFINE_TASKS:
            print(f'>>> no refine needed, copying as-is')
        else:
            print(f'>>> no refine rule for {task_name}, copying as-is')

        # Save refined predictions
        os.makedirs(os.path.dirname(save_tgt), exist_ok=True)
        with open(save_tgt, 'w', encoding='utf-8') as json_file:
            json.dump(pred_list, json_file, ensure_ascii=False, indent=4)
        print(f'>>> saved: {save_tgt}')


# ======================== Entry point ========================

if __name__ == '__main__':
    model_name_list = os.listdir(f'{RES_DIR}')
    model_name_list = sorted(model_name_list)
    print(f'Models found: {model_name_list}')

    for model_name in model_name_list:
        refine(model_name)
