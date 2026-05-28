# AVI-Bench Data Use Policy v1.0

> **TL;DR.** AVI-Bench is provided **for academic evaluation only**.
> You may **not** use it — in whole or in part — to train, fine-tune,
> distill, align, or otherwise update any machine-learning model.
> You may **not** redistribute or mirror the dataset.
> You may **not** crawl or batch-download it.
> You **must** cite our paper.
> Open a GitHub Issue titled "Removal request" if any bundled source
> content infringes your rights.

---

## 1. Scope

This Policy governs use of the **AVI-Bench dataset** and its
**AVI-Bench-PriSe** extension (collectively, the "Dataset"), including

* all annotations, question/answer pairs, splits, JSON metadata,
  bounding-box files, and any derived representations published under
  the name "AVI-Bench" or "AVI-Bench-PriSe";
* all processed media files distributed alongside the Dataset on
  <https://huggingface.co/datasets/FudanCVL/AVIBench> and any mirror;
* any subset, sample, embedding, summary, paraphrase, translation, or
  partial release of the above, irrespective of file format.

This Policy does **not** govern the AVI-Bench source code, which is
released under the MIT License (see `LICENSE`).

## 2. Base license

The Dataset is licensed under
[**Creative Commons Attribution-NonCommercial-NoDerivatives 4.0
International** (CC BY-NC-ND 4.0)](https://creativecommons.org/licenses/by-nc-nd/4.0/),
**with the additional Anti-Training Addendum in Section 3**.
Where the Addendum and CC BY-NC-ND 4.0 conflict, the Addendum prevails.

## 3. Anti-Training Addendum (binding)

Notwithstanding any other provision, you may **NOT** use the Dataset,
in whole or in part, directly or indirectly, for any of the following:

**(a) Model parameter updates.** Training, pre-training,
post-training, fine-tuning, instruction tuning, alignment (RLHF, DPO,
PPO, GRPO, or any equivalent), distillation, continual learning, or
any other procedure that updates the parameters of any
machine-learning model, including but not limited to

* large language models (LLMs);
* vision-language models (VLMs);
* audio-language models (ALMs);
* audio-visual, video-language, or omni-modal models (Omni-MLLMs);
* speech, music, or general-audio foundation models;
* diffusion, flow-matching, or other generative models;
* retrieval, embedding, or re-ranking models;
* any subsequent class of machine-learning model not yet known at the
  time of writing.

**(b) Training-data construction.** Any transformation of the Dataset
— including paraphrasing, translation, summarisation, captioning,
augmentation, synthetic data generation, or LLM-assisted relabeling —
whose output is then used for any purpose covered by clause (a).

**(c) Signal mining.** Mining the Dataset to recover or reconstruct
training signals for any model class enumerated in (a).

**(d) Redistribution.** Bulk redistribution, mirroring, or rehosting
of the Dataset, modified or not, on any platform other than the
official Hugging Face repository linked in Section 1.

**(e) Automated extraction.** Scraping, crawling, or batch downloading
of the project page or dataset repository in a manner inconsistent
with the `robots.txt` and HTML meta directives published at
<https://fudancvl.github.io/AVI-Bench/>.

**(f) Commercial use.** Any commercial use, including but not limited
to evaluation services sold or offered for a fee, paid API endpoints
whose correctness is benchmarked on the Dataset, and inclusion of the
Dataset in any commercial product.

## 4. Permitted use

You **may** use the Dataset to

* evaluate, benchmark, probe, or red-team pre-existing models that
  were trained without access to AVI-Bench;
* reproduce results reported in the AVI-Bench paper;
* support academic teaching, demonstrations, and qualitative analysis;
* conduct methodology research about evaluation itself — including new
  metrics, evaluation protocols, or aggregation schemes — provided no
  model parameters are updated using the Dataset.

## 5. Attribution

Any publication, technical report, blog post, presentation, or
derivative work that uses AVI-Bench must cite the paper:

```bibtex
@inproceedings{wang2026avibench,
  title     = {AVI-Bench: Toward Human-like Audio-Visual Intelligence of Omni-MLLMs},
  author    = {Wang, Yaoting and Zhang, Ziyi and Tu, Wenming and Xu, Shaoxuan and Du, Wenjie and Liang, Cheng and Wang, Weijun and Li, Yuanchao and Li, Guangyao and Fei, Hao and Li, Yuanchun and Ding, Henghui and Liu, Yunxin},
  booktitle = {Proceedings of the 43rd International Conference on Machine Learning (ICML)},
  year      = {2026}
}
```

## 6. Bundled source data

The Dataset incorporates content derived from several public sources
(including MusicAVQA, AV-Caps, AVHBench, and others — see the dataset
card on Hugging Face for the full attribution).  Each upstream source
retains its own license, which continues to apply to the underlying
media.  The Anti-Training Addendum in this Policy governs the
AVI-Bench annotations, organisation, and processing layered on top.

If you believe any bundled source content infringes your rights,
please open an issue at
<https://github.com/FudanCVL/AVI-Bench/issues> with the subject
**"Removal request"**.  We will respond within 14 calendar days.

## 7. No warranty

The Dataset is provided "AS IS", without warranty of any kind, express
or implied, including but not limited to warranties of merchantability,
fitness for a particular purpose, and non-infringement.  In no event
shall the AVI-Bench authors be liable for any claim, damages, or other
liability arising from use of the Dataset.

## 8. Acceptance

By downloading, accessing, or otherwise using the Dataset, you accept
this Policy in its entirety.  If you do not agree to any term, you
must not download or use the Dataset.

## 9. Versioning

This Policy may be updated to reflect newly emerging model classes or
crawler types.  Substantive changes will be announced on the project
page and accompanied by a version bump.  The version in force at the
time of your download remains binding for that copy.

---

*Policy version: 1.0.  Last updated: 2026-05-28.*
