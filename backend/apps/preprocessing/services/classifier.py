import difflib
import logging

from apps.preprocessing.data import INDUSTRY_KEYWORDS
from apps.preprocessing.services.cleaner import DataCleaner

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 0.85


def _word_similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def _fuzzy_match_keyword(keyword, text):
    tokens = text.split()
    keyword_words = keyword.split()

    if not tokens or not keyword_words:
        return False

    if len(keyword_words) == 1:
        k = keyword_words[0]
        best = max(_word_similarity(k, t) for t in tokens)
        return best >= FUZZY_THRESHOLD

    n = len(keyword_words)
    if len(tokens) < n:
        return False

    best = 0.0
    for i in range(len(tokens) - n + 1):
        window = tokens[i:i + n]
        ratios = [
            _word_similarity(kw, tw)
            for kw, tw in zip(keyword_words, window)
        ]
        avg = sum(ratios) / n
        if avg > best:
            best = avg

    return best >= FUZZY_THRESHOLD


class IndustryClassifier:
    def __init__(self, db_rules=None):
        self.industry_data = INDUSTRY_KEYWORDS
        self.db_rules = db_rules or []

    def classify(self, row_text, normalize=True):
        if normalize:
            row_text = DataCleaner.normalize_company_text(row_text)
        results = {}
        for industry_key, config in self.industry_data.items():
            score = self._score_industry(row_text, config)
            if score > 0:
                results[industry_key] = {
                    'name': config['name'],
                    'score': score,
                    'weight': config['weight'],
                }
        for rule in self.db_rules:
            if not rule.get('is_active', True):
                continue
            if rule.get('rule_type') != 'industry':
                continue
            rule_score = self._score_from_keywords(
                row_text, rule.get('keywords', []), rule.get('weight', 5)
            )
            if rule_score > 0:
                key = f'db_{rule["id"]}'
                results[key] = {
                    'name': rule['name'],
                    'score': rule_score,
                    'weight': rule.get('weight', 5),
                }
        return results

    def _score_industry(self, text, config):
        score = 0
        for kw in config.get('keywords_high', []):
            if _fuzzy_match_keyword(kw, text):
                score += 10
        for kw in config.get('keywords_medium', []):
            if _fuzzy_match_keyword(kw, text):
                score += 5
        return score

    def _score_from_keywords(self, text, keywords, weight):
        score = 0
        for kw in keywords:
            if _fuzzy_match_keyword(kw.lower(), text):
                score += weight
        return score

    def get_best_industry(self, row_text, normalize=True):
        results = self.classify(row_text, normalize=normalize)
        if not results:
            return None, 0
        best = max(results.items(), key=lambda x: x[1]['score'])
        return best[1]['name'], best[1]['score']

    def get_all_industries_summary(self, row_text, normalize=True):
        results = self.classify(row_text, normalize=normalize)
        if not results:
            return {}
        total = sum(r['score'] for r in results.values())
        if total == 0:
            return {}
        return {
            k: {
                'name': v['name'],
                'score': v['score'],
                'confidence': round(v['score'] / total * 100, 1),
            }
            for k, v in sorted(
                results.items(), key=lambda x: x[1]['score'], reverse=True
            )
        }
