import sys
import os
import json
import argparse
import glob
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from scripts.data_loader import AVIBenchTask
from scripts import utils
from scripts.definitions import TASK_TO_CATEGORY

def load_model(model_path, multi_gpu=True, backend=None):
    """Dispatch to a model adapter under models/.

    Backend selection (in order):
      1. explicit `backend` arg
      2. MODEL_BACKEND env var
      3. default: 'gemini' (OpenAI-compatible API client; works for any provider
         that exposes the OpenAI chat-completions interface, including Gemini,
         GPT-4o, Claude via gateways, and self-hosted servers).
    """
    if backend is None:
        backend = os.environ.get('MODEL_BACKEND', 'gemini')

    adapter_dir = os.path.join(os.path.dirname(__file__), 'models', backend)
    if not os.path.isdir(adapter_dir):
        raise ValueError(f"No adapter at models/{backend} (model_path={model_path!r})")
    sys.path.insert(0, adapter_dir)
    from importlib import import_module
    mod = import_module(f'models.{backend}.run')
    model, processor = mod.set_model(model_path, multi_gpu=multi_gpu)
    return model, processor, mod.get_response


def build_conversation(text_input, audio_list=None, image_list=None, video=None):
    content = []

    if image_list is not None:
        for img in image_list:
            content.append({"type": "image", "image": f"file://{os.path.abspath(img)}"})

    if audio_list is not None:
        for aud in audio_list:
            content.append({"type": "audio", "audio": f"file://{os.path.abspath(aud)}"})

    if video is not None:
        content.append({"type": "video", "video": f"file://{os.path.abspath(video)}", "nframes": 16})

    content.append({"type": "text", "text": text_input})

    conversation = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}],
        },
        {
            "role": "user",
            "content": content,
        },
    ]
    return conversation


def resolve_media_paths(data, task_path):
    audio_list = data['input'].get('audio_list', None)
    image_list = data['input'].get('image_list', None)
    video = data['input'].get('video', None)

    if audio_list is not None:
        for i, aud in enumerate(audio_list):
            audio_list[i] = aud.replace('./input', f'{task_path}/input')

    if image_list is not None:
        for i, img in enumerate(image_list):
            image_list[i] = img.replace('./input', f'{task_path}/input')

    if video is not None:
        video = video.replace('./input', f'{task_path}/input')

    return audio_list, image_list, video


def _process_one_sample(idx, dataset, task_path, task_name, model, processor, get_response_fn):
    """Run inference for a single sample. Returns dict with all fields needed by writer."""
    try:
        data = dataset[idx]
        _id = data['id']
        _task = data['task']
        _subtask = data.get('subtask', None)
        assert _task == task_name, f'Evaluating {task_name} but data has task={_task}'

        text_input = utils.get_real_input(data)
        audio_list, image_list, video = resolve_media_paths(data, task_path)

        for f_list, label in [(audio_list, 'audio'), (image_list, 'image')]:
            if f_list:
                for fp in f_list:
                    assert os.path.exists(fp), f'Not found - {label}: {fp}'
        if video is not None:
            assert os.path.exists(video), f'Not found - video: {video}'

        conversation = build_conversation(text_input, audio_list, image_list, video)
        result = get_response_fn(conversation, processor, model)
        pred_ans = result[0] if isinstance(result, list) and result else (result if not isinstance(result, list) else None)
        err = None
    except Exception as e:
        err = e
        pred_ans = None
        text_input = locals().get('text_input', '')
        audio_list = locals().get('audio_list', None)
        image_list = locals().get('image_list', None)
        video = locals().get('video', None)
        _id = locals().get('_id', idx)
        _task = task_name
        _subtask = locals().get('_subtask', None)

    return {
        "idx": idx, "id": _id, "task": _task, "subtask": _subtask,
        "predict": pred_ans, "err": err,
        "text_input": text_input, "audio_list": audio_list,
        "image_list": image_list, "video": video,
    }


def run_task(task_path, model, processor, get_response_fn, model_label, output_dir,
             n_samples=None, concurrency=1):
    task_name = os.path.basename(task_path)
    category = os.path.basename(os.path.dirname(task_path))

    if task_name not in TASK_TO_CATEGORY:
        print(f'>>> skip unknown task: {task_name}')
        return

    print(f'\n>>> task: {task_name} | category: {category} | concurrency={concurrency}')

    save_json = f'{output_dir}/{model_label}/tasks/{task_name}.json'
    log_file = f'{output_dir}/{model_label}/logs/{task_name}.log'
    os.makedirs(os.path.dirname(save_json), exist_ok=True)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    dataset = AVIBenchTask(task_path)

    try:
        with open(save_json, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        predictions = []

    total = len(dataset) if n_samples is None else min(n_samples, len(dataset))

    # Resume: a slot is "done" if it has a non-null predict. This handles both
    # legacy append-style files (len(preds) == total, all valid) and the new
    # position-indexed files where missing slots are None/null placeholders.
    pending_indices = []
    for i in range(total):
        if i < len(predictions):
            entry = predictions[i]
            if entry is None or entry.get('predict') in (None, ''):
                pending_indices.append(i)
        else:
            pending_indices.append(i)

    done_count = total - len(pending_indices)
    if done_count > 0:
        print(f'>>> resuming: {done_count}/{total} already complete, {len(pending_indices)} remaining')
    else:
        open(log_file, 'w').close()

    if not pending_indices:
        print(f'>>> task already complete: {task_name}')
        return

    io_lock = threading.Lock()

    # Pre-extend predictions with placeholders so concurrent writers can place
    # results at the correct idx (preserves dataset ordering — critical for
    # tasks like AVQA where the same id appears multiple times with different
    # questions; eval aligns by position).
    while len(predictions) < total:
        predictions.append(None)

    def write_record(rec):
        """Store record at its dataset idx and persist. Thread-safe."""
        pred_record = {
            "task": rec["task"], "subtask": rec["subtask"],
            "id": rec["id"], "predict": rec["predict"],
        }
        with io_lock:
            predictions[rec["idx"]] = pred_record
            with open(save_json, 'w', encoding='utf-8') as f:
                json.dump(predictions, f, ensure_ascii=False, indent=4)
            with open(log_file, 'a', encoding='utf-8') as lf:
                lf.write(f'========== [{rec["idx"]}] id={rec["id"]} task={rec["task"]} subtask={rec["subtask"]} ==========\n')
                lf.write(f'[INPUT]\n{rec["text_input"]}\n')
                if rec["audio_list"]:
                    lf.write(f'[AUDIO] {rec["audio_list"]}\n')
                if rec["image_list"]:
                    lf.write(f'[IMAGE] {rec["image_list"]}\n')
                if rec["video"]:
                    lf.write(f'[VIDEO] {rec["video"]}\n')
                lf.write(f'[OUTPUT]\n{rec["predict"]}\n\n')

    if concurrency <= 1:
        for idx in tqdm(pending_indices, desc=f'{task_name}'):
            rec = _process_one_sample(idx, dataset, task_path, task_name,
                                      model, processor, get_response_fn)
            if rec["err"] is not None:
                print(f'\n>>> err at idx={idx}: {rec["err"]}')
            write_record(rec)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_process_one_sample, idx, dataset, task_path, task_name,
                            model, processor, get_response_fn): idx
                for idx in pending_indices
            }
            with tqdm(total=len(futures), desc=f'{task_name}') as pbar:
                for fut in as_completed(futures):
                    try:
                        rec = fut.result()
                        if rec["err"] is not None:
                            print(f'\n>>> err at idx={rec["idx"]}: {rec["err"]}')
                        write_record(rec)
                    except Exception as e:
                        print(f'\n>>> future failed: {e}')
                    pbar.update(1)

    print(f'>>> done: {task_name} | {len(predictions)} predictions saved to {save_json}')


def main():
    parser = argparse.ArgumentParser(description='AVIBench Inference')
    parser.add_argument('--model_path', type=str,
                        default=os.environ.get('MODEL_PATH', 'gemini-2.5-pro'))
    parser.add_argument('--model_label', type=str,
                        default=os.environ.get('MODEL_LABEL', 'gemini-2.5-pro'))
    parser.add_argument('--tasks', type=str, nargs='+', default=None,
                        help='Task names to run, e.g. ASQA AMIC. If not set, run all tasks.')
    parser.add_argument('--output_dir', type=str,
                        default=os.environ.get('OUTPUT_DIR', './eval/user_outputs'))
    parser.add_argument('--data_root', type=str,
                        default=os.environ.get('DATA_ROOT', './data/levels'))
    parser.add_argument('--multi_gpu', action='store_true')
    parser.add_argument('--n_samples', type=int, default=None,
                        help='Limit samples per task (for smoke tests). Default: all samples.')
    parser.add_argument('--concurrency', type=int,
                        default=int(os.environ.get('CONCURRENCY', 1)),
                        help='Number of concurrent inference workers per task (default 1).')
    args = parser.parse_args()

    print(f'>>> model_path: {args.model_path}')
    print(f'>>> model_label: {args.model_label}')

    # Load model
    model, processor, get_response_fn = load_model(args.model_path, multi_gpu=args.multi_gpu)
    print('>>> model loaded successfully')

    # Discover tasks
    if args.tasks:
        task_paths = []
        for t in args.tasks:
            t = t.upper()
            cat = TASK_TO_CATEGORY.get(t)
            if cat is None:
                print(f'>>> unknown task: {t}, skipping')
                continue
            tp = os.path.join(args.data_root, cat, t)
            if os.path.exists(tp):
                task_paths.append(tp)
            else:
                print(f'>>> task path not found: {tp}')
    else:
        task_paths = sorted(glob.glob(f'{args.data_root}/*/*'))

    print(f'>>> tasks to run: {[os.path.basename(p) for p in task_paths]}')

    for task_path in task_paths:
        run_task(task_path, model, processor, get_response_fn, args.model_label, args.output_dir,
                 n_samples=args.n_samples, concurrency=args.concurrency)


if __name__ == '__main__':
    main()
