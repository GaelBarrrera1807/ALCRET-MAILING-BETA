import logging

from apps.preprocessing.data import WEIGHTS

logger = logging.getLogger(__name__)


class LeadFilter:
    def __init__(self, threshold=None):
        self.threshold = threshold or WEIGHTS.get('threshold_relevant', 30)

    def filter_records(self, scored_records):
        relevant = []
        discarded = []
        for record in scored_records:
            score_info = record.get('score_info', {})
            score = score_info.get('score', 0)
            if score >= self.threshold:
                relevant.append(record)
            else:
                discarded.append(record)
        logger.info(
            f'Filter (threshold={self.threshold}): '
            f'{len(relevant)} relevant, {len(discarded)} discarded'
        )
        return relevant, discarded

    def prioritize(self, records):
        def sort_key(r):
            score = r.get('score_info', {}).get('score', 0)
            priority_map = {'urgente': 4, 'alta': 3, 'media': 2, 'baja': 1, 'descartado': 0}
            priority = r.get('score_info', {}).get('priority', 'baja')
            return (priority_map.get(priority, 0), score)
        return sorted(records, key=sort_key, reverse=True)

    def summary_stats(self, all_records):
        if not all_records:
            return {
                'total': 0, 'relevant': 0, 'discarded': 0,
                'avg_score': 0, 'by_priority': {},
            }
        scores = [
            r.get('score_info', {}).get('score', 0) for r in all_records
        ]
        relevant = [
            r for r in all_records
            if r.get('score_info', {}).get('score', 0) >= self.threshold
        ]
        by_priority = {}
        for r in relevant:
            p = r.get('score_info', {}).get('priority', 'baja')
            by_priority[p] = by_priority.get(p, 0) + 1
        return {
            'total': len(all_records),
            'relevant': len(relevant),
            'discarded': len(all_records) - len(relevant),
            'threshold': self.threshold,
            'avg_score': round(sum(scores) / len(scores), 1) if scores else 0,
            'by_priority': by_priority,
        }
