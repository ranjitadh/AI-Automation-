import pytest
from django.test import TestCase
from apps.ai.humanization_engine import detect_ai_generated


class AIDetectionTests(TestCase):
    def test_ai_sounding_text_flagged(self):
        text = (
            "I am writing to apply for the Software Engineer position at Acme Corp. "
            "I am excited to bring my proven track record of results-driven innovation "
            "to your dynamic team. I am confident that my skills align perfectly with "
            "the requirements. Furthermore, I have a proven track record of leveraging "
            "cutting-edge technologies to streamline operations. I look forward to the "
            "opportunity of discussing how I can contribute to your world-class organization. "
            "Best regards, John Doe"
        )
        result = detect_ai_generated(text)
        self.assertGreater(result['score'], 0.3)
        self.assertTrue(len(result['indicators']) > 0)

    def test_natural_text_low_score(self):
        text = (
            "I saw Acme is hiring for a backend role. I have been building APIs with "
            "Python for about 5 years now, and I really like what your team is doing "
            "with the developer platform. At my current job, I built a system that "
            "handles about 10 million requests per day. I would love to chat about "
            "how I could help your team. Thanks for your time."
        )
        result = detect_ai_generated(text)
        self.assertLess(result['score'], 0.7)

    def test_buzzword_detection(self):
        text = "I leverage synergy to optimize scalable paradigms with robust cutting-edge innovation."
        result = detect_ai_generated(text)
        self.assertGreater(result['score'], 0.1)

    def test_ai_phrase_detection(self):
        text = "I am writing to apply for this position. I am excited to join your team."
        result = detect_ai_generated(text)
        self.assertTrue(any('AI phrase' in i for i in result['indicators']))

    def test_sentence_variance_detection(self):
        text = (
            "The candidate has experience with Python. The candidate knows Django. "
            "The candidate worked at Acme. The candidate has five years experience. "
            "The candidate is based in New York. The candidate prefers remote work. "
        )
        result = detect_ai_generated(text)
        self.assertIsNotNone(result['score'])

    def test_detection_method(self):
        result = detect_ai_generated("Some text here.")
        self.assertEqual(result['detection_method'], 'programmatic_pattern_analysis_v2')

    def test_suggestions_generated(self):
        result = detect_ai_generated(
            "I am writing to apply. I am excited. I am confident my skills align."
        )
        self.assertTrue(len(result['suggestions']) > 0)
