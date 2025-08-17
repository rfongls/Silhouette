from typing import Iterable
from torch.utils.data import Dataset, DataLoader

class SamplesDataset(Dataset):
    def __init__(self, samples: Iterable[dict], tokenizer, max_len=2048):
        self.samples = list(samples)
        self.tok = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        # Simple prompt template for SFT/KD
        prompt = f"### Instruction:\n{s['instruction']}\n\n### Input:\n{s['input']}\n\n### Response:\n"
        x = self.tok(prompt, truncation=True, max_length=self.max_len, return_tensors="pt")
        y = self.tok(s["output"], truncation=True, max_length=self.max_len, return_tensors="pt")
        return {
            "input_ids": x["input_ids"][0],
            "attention_mask": x["attention_mask"][0],
            "labels": y["input_ids"][0],
        }

def build_dataloader(samples_iter: Iterable[dict], tokenizer, batch_size=8, max_len=2048, shuffle=True):
    ds = SamplesDataset(samples_iter, tokenizer, max_len)
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle)
