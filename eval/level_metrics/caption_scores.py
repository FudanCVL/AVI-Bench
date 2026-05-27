
from nltk.translate.meteor_score import meteor_score
from rouge_score import rouge_scorer
# from pycocoevalcap.cider.cider import Cider
# from pycocoevalcap.spice.spice import Spice
from sentence_transformers import SentenceTransformer, util
import numpy as np

import nltk
# nltk.set_proxy('https://mirrors.tuna.tsinghua.edu.cn/nltk-data/')
# nltk.download('wordnet', download_dir='/home/share/nltk_data')
# nltk.download('omw-1.4', download_dir='/home/share/nltk_data')
nltk.data.path.append('/home/share/nltk_data')

# from . import test_cider
# nltk.download('punkt')
from nltk.tokenize import word_tokenize

def tokenize(sent):
    return ' '.join(word_tokenize(sent.lower()))

import os
os.environ['TRANSFORMERS_CACHE'] = './transformers_cache'  # Optional: set cache directory
os.environ['HUGGINGFACE_HUB_CACHE'] = './huggingface_cache'  # Optional: set HF cache directory
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # Required: HF mirror endpoint

SentenceTransformerModel = SentenceTransformer('all-MiniLM-L6-v2')

def evaluate_caption(pred_caption, ref_captions):
    """
    Evaluate predicted caption quality using METEOR, ROUGE-L, and SBERT_sim metrics.

    Args:
        pred_caption (str): Model-predicted caption.
        ref_captions (list of str): Reference caption list.

    Returns:
        dict: Dictionary containing scores for each metric.
    """
    results = {}

    # 1. METEOR
    tokenized_pred = pred_caption.split()
    tokenized_refs = [ref.split() for ref in ref_captions]
    meteor = meteor_score(tokenized_refs, tokenized_pred)
    results['METEOR'] = round(meteor, 5)

    # 2. ROUGE-L
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    rouge_l_scores = [scorer.score(ref, pred_caption)['rougeL'].fmeasure for ref in ref_captions]
    results['ROUGE_L'] = round(np.mean(rouge_l_scores).__float__(), 5)

    # # 3. CIDEr
    # ref = {
    #     '1': ['placeholder sentence here.'],
    #     '2': [pred_caption]
    # }
    # gt = {
    #     '1': ['placeholder sentence here.'],
    #     '2': ref_captions
    # }
    # cider_score_cls = test_cider.Scorer(ref, gt)
    # results['CIDEr'] = cider_score_cls.compute_scores()['CIDEr']
    # # (10 + 10) / 2 = 5
    # # (10 + 1) / 2 = 

    # # 4. SPICE
    # spice_scorer = Spice()
    # gts_spice = {0: ref_captions}
    # res_spice = {0: [pred_caption]}
    # spice_score, _ = spice_scorer.compute_score(gts_spice, res_spice)
    # results['SPICE'] = spice_score

    # 5. SBERT_sim
    model = SentenceTransformerModel
    pred_embedding = model.encode(pred_caption, convert_to_tensor=True)
    ref_embeddings = model.encode(ref_captions, convert_to_tensor=True)
    # Cosine similarity
    similarities = util.cos_sim(pred_embedding, ref_embeddings).cpu().numpy()[0]
    results['SBERT_sim'] = round(np.mean(similarities).__float__(), 5)
    # results['SBERT_sim'] = round(0)

    return results

# Example usage
if __name__ == "__main__":
    # Example input
    pred_caption = "A dog runs in the park."
    ref_captions = [
        "A dog is running in the park.",
        "The dog plays in the park.",
        "A puppy runs around in the park."
    ]

    # Evaluate
    scores = evaluate_caption(pred_caption, ref_captions)
    print('>> scores:', scores)

    # Print results
    print("Evaluation Scores:")
    for metric, score in scores.items():
        print(f"{metric}: {score:.4f}")