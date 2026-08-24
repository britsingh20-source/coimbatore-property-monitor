import unittest
from ai_daily_channel.src.discovery_engine import identity, score

class DiscoveryTests(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(identity("Tool.AI v2"),identity("Tool AI v2"))
    def test_practical_scores_higher(self):
        a={"title":"Free open source AI video app","summary":"local demo workflow","freshness":.9,"free_signal":1,"popularity":.8}
        b={"title":"Theoretical analysis","summary":"abstract","freshness":.6,"free_signal":.1,"popularity":.1}
        self.assertGreater(score(a),score(b))
if __name__=="__main__": unittest.main()
