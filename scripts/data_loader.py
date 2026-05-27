import torch
from torch.utils.data import Dataset

from . import utils


class AVIBenchTask(Dataset):
    def __init__(self, task_path):
        self.json_path = f'{task_path}/data.json'
        self.data_src = f'{task_path}/input'

        self.data = utils.read_json_to_list(self.json_path)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]
