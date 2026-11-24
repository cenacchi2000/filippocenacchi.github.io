import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import profile_metrics as metrics


class ProfileMetricsTests(unittest.TestCase):
    def test_scholar_total_not_recent_column(self):
        html = '<div id="gsc_prf_in">Filippo Cenacchi</div><table id="gsc_rsb_st"><tr><td>Citations</td><td>1,234</td><td>42</td></tr></table>'
        self.assertEqual(metrics.parse_citations(html), 1234)
        with self.assertRaises(ValueError):
            metrics.parse_citations(html.replace('Filippo Cenacchi', 'Someone Else'))

    def test_structured_followers_excludes_other_people_and_likes(self):
        people = [
            {'@type': 'Person', 'url': 'https://www.linkedin.com/in/someone-else/', 'interactionStatistic': {'interactionType': 'https://schema.org/FollowAction', 'userInteractionCount': 999}},
            {'@type': 'Person', 'url': metrics.LINKEDIN_URL, 'interactionStatistic': [
                {'interactionType': {'@type': 'LikeAction'}, 'userInteractionCount': 88},
                {'interactionType': {'@type': 'FollowAction'}, 'userInteractionCount': 20393}]}]
        self.assertEqual(metrics.parse_followers('<script type="application/ld+json">'+json.dumps(people)+'</script>'),20393)

    def test_visible_followers_exact_only(self):
        html = '<div class="top-card-layout"><h1>Filippo Cenacchi</h1><span>20,393 followers</span><span>500+ connections</span></div><aside>999 followers</aside>'
        self.assertEqual(metrics.parse_followers(html),20393)
        for bad in ['<h1>Sign in</h1>', html.replace('20,393', '20K'), html.replace('Filippo Cenacchi','Other Person'), html.replace('20,393','20,39')]:
            with self.assertRaises(ValueError):
                metrics.parse_followers(bad)

    def test_failure_keeps_last_verified_date_and_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'metrics.json'
            original = {'citations': {'count':36,'date':'23 November 2026'}, 'followers': {'count':20393,'date':'24 November 2026'}}
            path.write_text(json.dumps(original))
            with patch.object(metrics,'citations',side_effect=ValueError), patch.object(metrics,'followers',side_effect=ValueError):
                self.assertEqual(metrics.refresh(path),0)
                self.assertEqual(json.loads(path.read_text()),original)
            with patch.object(metrics,'citations',return_value=(37,'google-scholar')), patch.object(metrics,'followers',side_effect=ValueError):
                self.assertEqual(metrics.refresh(path),1)
                updated=json.loads(path.read_text())
                self.assertEqual(updated['followers'],original['followers'])
                self.assertEqual(updated['citations']['count'],37)


if __name__ == '__main__':
    unittest.main()
