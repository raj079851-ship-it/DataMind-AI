# -*- coding: utf-8 -*-
"""
Unit tests for AI Chart Recommendation Engine
Verifies:
1. Natural language column identification & entity resolution
2. Accurate chart selection based on column datatypes
3. Interactive Plotly figure generation
4. Plain-language explanation generation
5. Statistical pattern and insight detection
6. Automated collection generation for "Create the best charts for this dataset"
7. Resilient edge case handling
"""

import unittest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from modules.ai_chart_recommender import AIChartRecommender, default_chart_recommender


class TestAIChartRecommender(unittest.TestCase):
    def setUp(self):
        self.recommender = AIChartRecommender()
        np.random.seed(42)
        n = 100
        self.df = pd.DataFrame({
            "sales": np.random.uniform(100, 1000, n),
            "profit": np.random.uniform(10, 300, n),
            "contract": np.random.choice(["Month-to-month", "One year", "Two year"], n),
            "tenure": np.random.randint(1, 72, n),
            "churn": np.random.choice(["Yes", "No"], n, p=[0.25, 0.75]),
            "order_date": pd.date_range("2024-01-01", periods=n, freq="D")
        })
        # Add correlated profit
        self.df["profit"] = self.df["sales"] * 0.35 + np.random.normal(0, 15, n)

    def test_identify_relationship_between_sales_and_profit(self):
        cols, intent, meta = self.recommender.identify_columns(
            "Show me the relationship between sales and profit.",
            self.df
        )
        self.assertEqual(len(cols), 2)
        self.assertIn("sales", cols)
        self.assertIn("profit", cols)
        self.assertEqual(intent, "correlation")

    def test_identify_distribution_intent(self):
        cols, intent, meta = self.recommender.identify_columns(
            "Show me the distribution of sales",
            self.df
        )
        self.assertIn("sales", cols)
        self.assertEqual(intent, "distribution")

    def test_identify_best_charts_intent(self):
        cols, intent, meta = self.recommender.identify_columns(
            "Create the best charts for this dataset",
            self.df
        )
        self.assertEqual(intent, "best_collection")

    def test_recommend_scatter_for_two_numerics(self):
        rec = self.recommender.recommend_chart_type(self.df, ["sales", "profit"])
        self.assertEqual(rec["chart_type"], "scatter")
        self.assertIn("scatter plot is recommended", rec["rationale"].lower())
        self.assertIn("continuous numerical variables", rec["rationale"].lower())

    def test_recommend_distribution_for_single_numeric(self):
        rec = self.recommender.recommend_chart_type(self.df, ["sales"])
        self.assertEqual(rec["chart_type"], "distribution")
        self.assertIn("histogram", rec["rationale"].lower())

    def test_recommend_donut_for_low_cardinality_categorical(self):
        rec = self.recommender.recommend_chart_type(self.df, ["contract"])
        self.assertIn(rec["chart_type"], ["donut", "horizontal_bar"])

    def test_recommend_line_for_date_and_numeric(self):
        rec = self.recommender.recommend_chart_type(self.df, ["order_date", "sales"])
        self.assertEqual(rec["chart_type"], "line")
        self.assertIn("line chart", rec["rationale"].lower())

    def test_recommend_box_or_bar_for_categorical_and_numeric(self):
        rec = self.recommender.recommend_chart_type(self.df, ["contract", "sales"])
        self.assertIn(rec["chart_type"], ["bar", "box", "donut"])

    def test_generate_visualization_returns_plotly_figure(self):
        rec = self.recommender.recommend_chart_type(self.df, ["sales", "profit"])
        fig = self.recommender.generate_visualization(self.df, rec)
        self.assertIsInstance(fig, go.Figure)
        self.assertTrue(len(fig.data) > 0)

    def test_generate_explanation_contains_interpretation(self):
        rec = self.recommender.recommend_chart_type(self.df, ["sales", "profit"])
        explanation = self.recommender.generate_explanation(self.df, rec)
        self.assertIsInstance(explanation, str)
        self.assertIn("Why this chart", explanation)
        self.assertIn("Interpretation Guide", explanation)

    def test_detect_important_patterns_scatter(self):
        rec = self.recommender.recommend_chart_type(self.df, ["sales", "profit"])
        patterns = self.recommender.detect_important_patterns(self.df, rec)
        self.assertIsInstance(patterns, list)
        self.assertTrue(len(patterns) >= 1)
        # Should detect correlation
        pattern_text = " ".join(patterns)
        self.assertIn("Correlation", pattern_text)
        self.assertIn("linear relationship", pattern_text)

    def test_detect_important_patterns_categorical(self):
        rec = self.recommender.recommend_chart_type(self.df, ["contract"])
        patterns = self.recommender.detect_important_patterns(self.df, rec)
        self.assertTrue(len(patterns) >= 1)
        self.assertIn("Dominance", " ".join(patterns))

    def test_recommend_from_query_single_chart(self):
        res = self.recommender.recommend_from_query(
            "Show me the relationship between sales and profit.",
            self.df
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["mode"], "single")
        self.assertEqual(res["chart_type"], "scatter")
        self.assertIsInstance(res["figure"], go.Figure)
        self.assertIn("scatter plot is recommended", res["rationale"].lower())
        self.assertTrue(len(res["patterns"]) >= 1)

    def test_recommend_from_query_best_charts_collection(self):
        res = self.recommender.recommend_from_query(
            "Create the best charts for this dataset",
            self.df
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["mode"], "collection")
        self.assertIn("collection", res)
        self.assertTrue(len(res["collection"]) >= 3)
        for item in res["collection"]:
            self.assertIn("title", item)
            self.assertIn("chart_type", item)
            self.assertIsInstance(item["figure"], go.Figure)
            self.assertIn("explanation", item)
            self.assertIn("patterns", item)

    def test_empty_dataframe_handling(self):
        empty_df = pd.DataFrame()
        res = self.recommender.recommend_from_query("relationship between sales and profit", empty_df)
        self.assertEqual(res["status"], "error")


if __name__ == "__main__":
    unittest.main()
