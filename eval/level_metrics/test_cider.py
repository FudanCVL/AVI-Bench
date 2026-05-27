from pycocoevalcap.cider.cider import Cider

class Scorer():
    def __init__(self, ref, gt):
        self.ref = ref
        self.gt = gt
        # print('setting up scorers...')
        self.scorers = [
            (Cider(), "CIDEr"),
        ]
    
    def compute_scores(self):
        total_scores = {}
        for scorer, method in self.scorers:
            # print('computing %s score...' % (scorer.method()))
            score, scores = scorer.compute_score(self.gt, self.ref)
            if type(method) == list:
                for sc, scs, m in zip(score, scores, method):
                    # print("%s: %0.3f" % (m, sc))
                    ...
                total_scores["Bleu"] = score
            else:
                # print("%s: %0.3f" % (method, score))
                total_scores[method] = score
        
        # print('*****DONE*****')
        # for key, value in total_scores.items():
        #     # print('{}:{}'.format(key, value))
        #     ...
        return total_scores


if __name__ == '__main__':
    ref = {
        '1': ['mamba out of the day'],
        # '2': ['go down the stairs and stop at the bottom .'],
        # '3': ['what can i say'],
        '4': ['the cat is over here.']
    }
    gt = {
        # '1': ['Walk down the steps and stop at the bottom. ', 'Go down the stairs and wait at the bottom.'],
        # '2': ['Walk out of down the steps and stop at the bottom. ', 'Go down the stairs and wait at the bottom.'],
        '1': ['mamba out of the day'],
        # '2': ['go down the stairs and stop at the bottom go down the stairs and stop at the bottom go down the stairs and stop at the bottom .'],
        # '3': ['what can i say'],
        '4': ['the cat is over here.']
    }
    scorer = Scorer(ref, gt)
    scorer.compute_scores()