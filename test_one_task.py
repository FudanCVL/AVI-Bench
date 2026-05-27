"""
Worker script: test a single task with N samples.
Called by test_all_tasks.py in a subprocess for CUDA isolation.

Usage: python test_one_task.py TASK_NAME [N_TEST] [MODEL_PATH] [DATA_ROOT]
Outputs a single JSON line to stdout with {"status": ..., "results"|"detail": ...}
"""
import os
import sys
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.data_loader import AVIBenchTask
from scripts import utils
from scripts.definitions import TASK_TO_CATEGORY


def _pick_backend(model_path: str) -> str:
    return os.environ.get('MODEL_BACKEND', 'gemini')


def _load_adapter(model_path):
    backend = _pick_backend(model_path)
    from importlib import import_module
    mod = import_module(f'models.{backend}.run')
    return mod.set_model, mod.get_response, backend

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

    return [
        {"role": "system", "content": [{"type": "text", "text": "You are a helpful assistant."}]},
        {"role": "user", "content": content},
    ]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('task_name', type=str)
    parser.add_argument('n_test', type=int, nargs='?', default=5)
    parser.add_argument('model_path', type=str, nargs='?',
                        default=os.environ.get('MODEL_PATH', 'gemini-2.5-pro'))
    parser.add_argument('data_root', type=str, nargs='?',
                        default=os.environ.get('DATA_ROOT', './data/levels'))
    parser.add_argument('--multi_gpu', action='store_true')
    args = parser.parse_args()

    task_name = args.task_name
    category = TASK_TO_CATEGORY[task_name]
    task_path = os.path.join(args.data_root, category, task_name)

    if not os.path.exists(task_path):
        print(json.dumps({"status": "SKIP", "detail": f"path not found: {task_path}"}))
        return

    set_model, get_response, backend = _load_adapter(args.model_path)
    print(f"Loading model... (backend={backend}, multi_gpu={args.multi_gpu})", file=sys.stderr)
    model, processor = set_model(args.model_path, multi_gpu=args.multi_gpu)
    print(f"Model loaded.", file=sys.stderr)

    dataset = AVIBenchTask(task_path)
    n = min(args.n_test, len(dataset))
    results = []

    for idx in range(n):
        data = dataset[idx]
        text_input = utils.get_real_input(data)
        try:
            audio_list, image_list, video = resolve_media_paths(data, task_path)

            for f_list in [audio_list, image_list]:
                if f_list:
                    for fp in f_list:
                        assert os.path.exists(fp), f'Missing: {fp}'
            if video is not None:
                assert os.path.exists(video), f'Missing video: {video}'

            conversation = build_conversation(text_input, audio_list, image_list, video)
            result = get_response(conversation, processor, model)
            pred = result[0] if isinstance(result, list) else result
            results.append(pred)
            print(f"  [{idx}] OK", file=sys.stderr)
        except Exception as e:
            print(json.dumps({"status": "FAIL", "detail": f"idx={idx}: {e}"}))
            traceback.print_exc(file=sys.stderr)
            return
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass

    print(json.dumps({"status": "OK", "results": results}))


if __name__ == '__main__':
    main()
