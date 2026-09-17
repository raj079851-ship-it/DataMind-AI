# -*- coding: utf-8 -*-
"""
AI Chart Recommendation Engine
- Natural language query understanding & column entity extraction
- Heuristic and statistical chart selection
- Interactive Plotly visualization generation
- Plain-language chart explanations and architectural rationale
- Automated statistical pattern and insight detection
- Multi-chart auto-generation for dataset profiling ("Create the best charts for this dataset")
"""

import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, Tuple


# Semantic Synonym Mappings for Column Entity Resolution
COLUMN_SYNONYMS: Dict[str, List[str]] = {
    "sales": ["sales", "monthlycharges", "totalcharges", "revenue", "amount", "charge", "price", "spending"],
    "profit": ["profit", "margin", "net_income", "earnings", "returns", "gain", "markup"],
    "revenue": ["revenue", "monthlycharges", "totalcharges", "sales", "turnover", "income"],
    "churn": ["churn", "attrition", "exited", "status", "cancelled", "left"],
    "cost": ["cost", "expense", "fee", "charges", "price"],
    "tenure": ["tenure", "months", "duration", "age", "period", "loyalty"],
    "contract": ["contract", "plan", "subscription", "agreement", "type"],
    "payment": ["payment", "paymentmethod", "billing", "method"],
    "charges": ["monthlycharges", "totalcharges", "charges", "amount", "fee"],
    "price": ["price", "unitprice", "cost", "value", "fare"],
    "quantity": ["quantity", "volume", "units", "items", "count"],
    "discount": ["discount", "rebate", "concession"],
    "age": ["age", "seniorcitizen", "tenure", "senior"],
    "gender": ["gender", "sex"],
    "customer": ["customerid", "customer", "client", "user", "account"],
    "date": ["date", "timestamp", "year", "month", "day", "created_at", "order_date"],
    "category": ["category", "type", "class", "segment", "department"],
    "rating": ["rating", "score", "satisfaction", "stars", "feedback"],
    "salary": ["salary", "wage", "compensation", "income", "pay"]
}

CHART_LABELS: Dict[str, str] = {
    "scatter": "Scatter Plot with Trendline",
    "distribution": "Distribution Histogram & KDE",
    "bar": "Grouped Column / Bar Chart",
    "box": "Box Plot with Outliers",
    "donut": "Executive Donut Chart",
    "horizontal_bar": "Ranked Horizontal Bar Chart",
    "line": "Time-Series Line Chart",
    "categorical_cross": "Categorical Cross-Tabulation",
    "correlation_heatmap": "Feature Collinearity Heatmap",
    "heatmap": "Correlation Heatmap Matrix"
}


class AIChartRecommender:
    """Intelligent chart recommendation, generation, explanation, and pattern detection engine."""

    def __init__(self):
        pass

    def identify_columns(self, query: str, df: pd.DataFrame) -> Tuple[List[str], str, Dict[str, Any]]:
        """
        Parses user natural language query to identify relevant dataset columns and intent.
        Returns: (matched_columns, query_intent, metadata)
        """
        q = (query or "").lower().strip()
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
        date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c]) or any(k in c.lower() for k in ["date", "time", "year"])]

        # 1. Intent Detection
        intent = "general"
        if any(w in q for w in ["best charts", "best chart", "collection", "useful visualization", "dashboard", "overview", "auto chart", "show me charts", "recommend charts"]):
            return [], "best_collection", {"matched_concept": "all"}
        elif any(w in q for w in ["relationship", "correlation", "vs", "versus", "scatter", "affect", "impact", "influence", "correlated", "covary"]):
            intent = "correlation"
        elif any(w in q for w in ["distribution", "histogram", "spread", "skew", "density", "range", "frequency of"]):
            intent = "distribution"
        elif any(w in q for w in ["trend", "over time", "timeline", "history", "trajectory", "growth"]):
            intent = "trend"
        elif any(w in q for w in ["proportion", "share", "percentage", "composition", "donut", "pie", "breakdown"]):
            intent = "composition"
        elif any(w in q for w in ["compare", "comparison", "across", "by", "difference"]):
            intent = "comparison"

        matched: List[str] = []

        # 2. Extract "between X and Y" specifically
        rel_match = re.search(r'(?:between|of|for)\s+([a-zA-Z0-9_\s]+?)\s+(?:and|&|vs|versus)\s+([a-zA-Z0-9_\s]+)', q)
        if rel_match:
            candidate1, candidate2 = rel_match.group(1).strip(), rel_match.group(2).strip()
            is_corr_intent = (intent == "correlation")
            c1_match = self._find_best_column_match(candidate1, df, prefer_numeric=is_corr_intent)
            c2_match = self._find_best_column_match(candidate2, df, prefer_numeric=is_corr_intent)
            if c1_match:
                matched.append(c1_match)
            if c2_match and c2_match not in matched:
                matched.append(c2_match)

        # 3. Direct column name matches
        if len(matched) < 2:
            for col in df.columns:
                clean_col = col.lower().replace("_", " ")
                # Check if exact column name appears in query
                if clean_col in q or col.lower() in q:
                    if col not in matched:
                        matched.append(col)

        # 4. Synonym-based entity resolution
        if len(matched) < 2:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', q)
            for w in words:
                if w in ["show", "the", "and", "between", "for", "with", "this", "that", "give", "create", "plot", "chart", "make"]:
                    continue
                # Check synonym dictionary
                for concept, synonyms in COLUMN_SYNONYMS.items():
                    if w == concept or w in synonyms:
                        # Find a column in df that matches any synonym for this concept
                        for syn in synonyms:
                            col_found = next((c for c in df.columns if syn == c.lower() or syn in c.lower().replace("_", "")), None)
                            if col_found and col_found not in matched:
                                matched.append(col_found)
                                break
                    if len(matched) >= 2:
                        break
                if len(matched) >= 2:
                    break

        # 5. Smart Heuristic Fallback if columns are still underspecified
        if not matched:
            if intent == "trend" and date_cols and num_cols:
                matched = [date_cols[0], num_cols[0]]
            elif intent == "distribution" and num_cols:
                # Pick highest variance numeric column
                variances = {c: df[c].var() for c in num_cols if pd.notna(df[c].var())}
                top_col = max(variances, key=variances.get) if variances else num_cols[0]
                matched = [top_col]
            elif intent in ["correlation", "general"] and len(num_cols) >= 2:
                # Pick top correlated pair
                matched = self._find_highest_correlated_pair(df, num_cols)
            elif cat_cols and num_cols:
                matched = [cat_cols[0], num_cols[0]]
            elif len(num_cols) >= 1:
                matched = [num_cols[0]]
            elif len(cat_cols) >= 1:
                matched = [cat_cols[0]]

        return matched, intent, {"query": query}

    def _find_best_column_match(self, term: str, df: pd.DataFrame, prefer_numeric: bool = False) -> Optional[str]:
        """Resolves a raw string term to the closest matching DataFrame column."""
        term_clean = term.lower().strip().replace("_", " ")
        # 1. Exact match
        for col in df.columns:
            if col.lower() == term_clean or col.lower().replace("_", " ") == term_clean:
                return col

        # 2. Word boundary match
        for col in df.columns:
            col_words = col.lower().replace("_", " ").split()
            if term_clean in col_words:
                return col

        # 3. Synonym match (prefer numeric if requested or for metrics)
        for concept, synonyms in COLUMN_SYNONYMS.items():
            if term_clean == concept or term_clean in synonyms:
                matching_cols = []
                for syn in synonyms:
                    for col in df.columns:
                        if syn == col.lower() or syn == col.lower().replace("_", " ") or syn in col.lower().replace("_", " ").split():
                            if col not in matching_cols:
                                matching_cols.append(col)
                if matching_cols:
                    if prefer_numeric:
                        num_matches = [c for c in matching_cols if pd.api.types.is_numeric_dtype(df[c])]
                        if num_matches:
                            return num_matches[0]
                    return matching_cols[0]

        # 4. Substring match
        for col in df.columns:
            if term_clean in col.lower() or col.lower() in term_clean:
                return col
        return None

    def _find_highest_correlated_pair(self, df: pd.DataFrame, num_cols: List[str]) -> List[str]:
        """Identifies the pair of continuous variables with the highest absolute correlation."""
        if len(num_cols) < 2:
            return num_cols
        corr_matrix = df[num_cols].corr().abs()
        corr_arr = corr_matrix.to_numpy(copy=True)
        np.fill_diagonal(corr_arr, 0)
        corr_clean = pd.DataFrame(corr_arr, index=corr_matrix.index, columns=corr_matrix.columns)
        max_val = corr_clean.max().max()
        if pd.notna(max_val) and max_val > 0:
            stack = corr_clean.stack()
            c1, c2 = stack.idxmax()
            return [c1, c2]
        return num_cols[:2]


    def recommend_chart_type(self, df: pd.DataFrame, matched_cols: List[str], intent: str = "general") -> Dict[str, Any]:
        """
        Selects the optimal chart type, axis assignments, and architectural rationale based on column datatypes.
        """
        if not matched_cols or any(c not in df.columns for c in matched_cols):
            # Fallback
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if num_cols:
                matched_cols = num_cols[:2] if len(num_cols) >= 2 else [num_cols[0]]
            else:
                matched_cols = list(df.columns[:2]) if len(df.columns) >= 2 else list(df.columns[:1])

        if not matched_cols:
            return {
                "chart_type": "none",
                "col_x": None,
                "col_y": None,
                "title": "No Features Available",
                "rationale": "No suitable columns available in the dataset for visualization."
            }

        # Single Column
        if len(matched_cols) == 1:
            col = matched_cols[0]
            is_num = pd.api.types.is_numeric_dtype(df[col])
            is_date = pd.api.types.is_datetime64_any_dtype(df[col]) or any(k in col.lower() for k in ["date", "time", "year"])

            if is_date:
                return {
                    "chart_type": "line",
                    "col_x": col,
                    "col_y": None,
                    "title": f"Timeline Activity of {col}",
                    "rationale": f"A time-series line chart is recommended because '{col}' is a temporal dimension tracking event progression."
                }
            elif is_num:
                return {
                    "chart_type": "distribution",
                    "col_x": col,
                    "col_y": None,
                    "title": f"Distribution Analysis of {col}",
                    "rationale": f"A histogram with KDE density curve is recommended because '{col}' is a continuous numerical variable, highlighting central tendency, skewness, and outliers."
                }
            else:
                n_uniq = df[col].nunique()
                if n_uniq <= 6:
                    return {
                        "chart_type": "donut",
                        "col_x": col,
                        "col_y": None,
                        "title": f"Category Share of {col}",
                        "rationale": f"A donut chart is recommended because '{col}' is a low-cardinality categorical variable ({n_uniq} unique segments), providing clean proportional share visualization."
                    }
                else:
                    return {
                        "chart_type": "horizontal_bar",
                        "col_x": col,
                        "col_y": None,
                        "title": f"Frequency Breakdown of {col}",
                        "rationale": f"A ranked horizontal bar chart is recommended because '{col}' has {n_uniq} distinct categories, ensuring readable segment labels without clutter."
                    }

        # Two Columns
        c1, c2 = matched_cols[0], matched_cols[1]
        is_num1 = pd.api.types.is_numeric_dtype(df[c1])
        is_num2 = pd.api.types.is_numeric_dtype(df[c2])
        is_date1 = pd.api.types.is_datetime64_any_dtype(df[c1]) or any(k in c1.lower() for k in ["date", "time", "year"])
        is_date2 = pd.api.types.is_datetime64_any_dtype(df[c2]) or any(k in c2.lower() for k in ["date", "time", "year"])

        # 1. Date + Numeric -> Line Chart
        if (is_date1 and is_num2) or (is_date2 and is_num1):
            date_col = c1 if is_date1 else c2
            val_col = c2 if is_date1 else c1
            return {
                "chart_type": "line",
                "col_x": date_col,
                "col_y": val_col,
                "title": f"{val_col} Trend Over Time ({date_col})",
                "rationale": f"A time-series line chart is recommended because '{date_col}' represents time and '{val_col}' is continuous, optimal for tracking momentum, peaks, and seasonality."
            }

        # 2. Both Numeric -> Scatter Plot with Trendline
        if is_num1 and is_num2:
            return {
                "chart_type": "scatter",
                "col_x": c1,
                "col_y": c2,
                "title": f"Relationship: {c1} vs {c2}",
                "rationale": f"A scatter plot is recommended because both {c1} and {c2} are continuous numerical variables, perfectly revealing correlation, dispersion, and anomalous outliers."
            }

        # 3. Categorical + Numeric -> Bar Chart, Box Plot, or Donut
        if (not is_num1 and is_num2) or (is_num1 and not is_num2):
            cat_col = c1 if not is_num1 else c2
            num_col = c2 if not is_num1 else c1
            n_cat = df[cat_col].nunique()

            if intent == "distribution" or n_cat > 8:
                return {
                    "chart_type": "box",
                    "col_x": cat_col,
                    "col_y": num_col,
                    "title": f"{num_col} Distribution by {cat_col}",
                    "rationale": f"A box plot is recommended because comparing continuous '{num_col}' across '{cat_col}' ({n_cat} segments) reveals median, interquartile range (IQR), and cluster variances."
                }
            elif intent == "composition":
                return {
                    "chart_type": "donut",
                    "col_x": cat_col,
                    "col_y": num_col,
                    "title": f"{num_col} Contribution by {cat_col}",
                    "rationale": f"A donut chart is recommended because '{cat_col}' has {n_cat} compact segments, providing an executive proportional view of '{num_col}'."
                }
            else:
                return {
                    "chart_type": "bar",
                    "col_x": cat_col,
                    "col_y": num_col,
                    "title": f"Total {num_col} by {cat_col}",
                    "rationale": f"A grouped column bar chart is recommended because it cleanly ranks categorical segments in '{cat_col}' against continuous aggregate '{num_col}'."
                }

        # 4. Both Categorical -> Grouped / Stacked Column Chart
        return {
            "chart_type": "categorical_cross",
            "col_x": c1,
            "col_y": c2,
            "title": f"Cross-Tabulation: {c1} vs {c2}",
            "rationale": f"A segmented cross-tabulation chart is recommended because both '{c1}' and '{c2}' are categorical factors, illuminating interaction rates."
        }

    def generate_visualization(self, df: pd.DataFrame, rec: Dict[str, Any]) -> Optional[go.Figure]:
        """Constructs and returns an interactive, theme-styled Plotly Figure."""
        if rec is None or rec.get("chart_type") == "none" or df is None or df.empty:
            return None
        chart_type = rec.get("chart_type", "distribution")
        x = rec.get("col_x")
        y = rec.get("col_y")
        title = rec.get("title", "AI Recommended Visualization")
        theme_template = "plotly_dark"

        # Theme color palette
        colors = px.colors.qualitative.Plotly

        if chart_type == "scatter":
            try:
                fig = px.scatter(
                    df, x=x, y=y,
                    trendline="ols",
                    title=f"<b>{title}</b>",
                    template=theme_template,
                    opacity=0.75,
                    labels={x: str(x).replace("_", " ").title(), y: str(y).replace("_", " ").title()}
                )
            except Exception:
                fig = px.scatter(
                    df, x=x, y=y,
                    title=f"<b>{title}</b>",
                    template=theme_template,
                    opacity=0.75,
                    labels={x: str(x).replace("_", " ").title(), y: str(y).replace("_", " ").title()}
                )
            fig.update_traces(marker=dict(size=8, color="#6366f1", line=dict(width=1, color="#e0e7ff")))

        elif chart_type == "distribution":
            fig = px.histogram(
                df, x=x,
                marginal="box",
                nbins=35,
                title=f"<b>{title}</b>",
                template=theme_template,
                color_discrete_sequence=["#38bdf8"]
            )
            fig.update_layout(bargap=0.08)

        elif chart_type == "bar":
            agg_df = df.groupby(x, dropna=False)[y].mean().reset_index()
            agg_df = agg_df.sort_values(by=y, ascending=False).head(15)
            fig = px.bar(
                agg_df, x=x, y=y,
                title=f"<b>{title} (Average)</b>",
                template=theme_template,
                color=y,
                color_continuous_scale="Viridis",
                text_auto=".2s"
            )

        elif chart_type == "horizontal_bar":
            val_counts = df[x].value_counts().reset_index().head(15)
            val_counts.columns = [x, "count"]
            fig = px.bar(
                val_counts, x="count", y=x,
                orientation="h",
                title=f"<b>{title}</b>",
                template=theme_template,
                color="count",
                color_continuous_scale="Blues",
                text_auto=True
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))

        elif chart_type == "box":
            fig = px.box(
                df, x=x, y=y,
                color=x,
                title=f"<b>{title}</b>",
                template=theme_template,
                points="outliers"
            )

        elif chart_type == "donut":
            if y:
                agg_df = df.groupby(x, dropna=False)[y].sum().reset_index()
                fig = px.pie(
                    agg_df, names=x, values=y,
                    hole=0.45,
                    title=f"<b>{title}</b>",
                    template=theme_template,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
            else:
                val_counts = df[x].value_counts().reset_index().head(8)
                val_counts.columns = [x, "count"]
                fig = px.pie(
                    val_counts, names=x, values="count",
                    hole=0.45,
                    title=f"<b>{title}</b>",
                    template=theme_template,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
            fig.update_traces(textinfo="percent+label")

        elif chart_type == "line":
            # Attempt to sort by date column
            plot_df = df.copy()
            if x in plot_df.columns:
                try:
                    plot_df[x] = pd.to_datetime(plot_df[x], errors="ignore")
                    plot_df = plot_df.sort_values(by=x)
                except Exception:
                    pass
            if y:
                # Group by date if duplicated
                agg_df = plot_df.groupby(x, as_index=False)[y].mean().head(200)
                fig = px.line(
                    agg_df, x=x, y=y,
                    title=f"<b>{title}</b>",
                    template=theme_template,
                    markers=True
                )
                fig.update_traces(line=dict(color="#10b981", width=3))
            else:
                # Frequency over time
                counts = plot_df[x].value_counts().sort_index().reset_index()
                counts.columns = [x, "events"]
                fig = px.line(
                    counts, x=x, y="events",
                    title=f"<b>{title}</b>",
                    template=theme_template,
                    markers=True
                )
                fig.update_traces(line=dict(color="#38bdf8", width=3))

        elif chart_type == "categorical_cross":
            ct = pd.crosstab(df[x], df[y], normalize="index") * 100
            ct_reset = ct.reset_index().melt(id_vars=x, var_name=y, value_name="Percentage (%)")
            fig = px.bar(
                ct_reset, x=x, y="Percentage (%)",
                color=y,
                barmode="group",
                title=f"<b>{title}</b>",
                template=theme_template
            )

        elif chart_type == "correlation_heatmap":
            num_df = df.select_dtypes(include=[np.number])
            corr = num_df.corr().round(2)
            fig = px.imshow(
                corr, text_auto=True,
                title=f"<b>{title}</b>",
                template=theme_template,
                color_continuous_scale="RdBu_r",
                aspect="auto"
            )

        else:
            # Universal fallback
            col = x or df.columns[0]
            fig = px.histogram(df, x=col, title=f"<b>{title}</b>", template=theme_template)

        fig.update_layout(
            margin=dict(l=40, r=40, t=60, b=40),
            paper_bgcolor="rgba(15, 23, 42, 0.4)",
            plot_bgcolor="rgba(15, 23, 42, 0.2)",
            font=dict(family="Inter, -apple-system, sans-serif", color="#f8fafc")
        )
        return fig

    def generate_explanation(self, df: pd.DataFrame, rec: Dict[str, Any]) -> str:
        """Produces a human-readable AI explanation of the chart structure and interpretation."""
        if not rec or rec.get("chart_type") == "none" or df is None or df.empty:
            return rec.get("rationale", "No visualization explanation available.") if rec else "No data available."
        chart_type = rec.get("chart_type", "distribution")
        x = rec.get("col_x")
        y = rec.get("col_y")
        rationale = rec.get("rationale", "")

        if chart_type == "scatter":
            r_val = df[x].corr(df[y]) if x in df and y in df else None
            corr_text = f" Pearson correlation is r = {r_val:.2f}." if r_val is not None and pd.notna(r_val) else ""
            return (
                f"**Why this chart:** {rationale}\n\n"
                f"**Interpretation Guide:** Each point corresponds to an individual observation. "
                f"The horizontal X-axis maps `{x}` while the vertical Y-axis measures `{y}`. "
                f"The superimposed regression trendline demonstrates directional affinity.{corr_text}"
            )
        elif chart_type == "distribution":
            mean_val = df[x].mean() if x in df else 0
            std_val = df[x].std() if x in df else 0
            return (
                f"**Why this chart:** {rationale}\n\n"
                f"**Interpretation Guide:** The histogram bars illustrate value frequencies across uniform bins, "
                f"while the upper boxplot highlights median, IQR boundaries, and extreme outliers. "
                f"Empirical mean is {mean_val:,.2f} (±{std_val:,.2f} std dev)."
            )
        elif chart_type in ["bar", "horizontal_bar"]:
            return (
                f"**Why this chart:** {rationale}\n\n"
                f"**Interpretation Guide:** Segments in `{x}` are ranked by aggregate volume or mean metric value. "
                f"Bar lengths provide an immediate visual benchmark of leader vs lagging cohorts."
            )
        elif chart_type == "donut":
            return (
                f"**Why this chart:** {rationale}\n\n"
                f"**Interpretation Guide:** Arc lengths represent relative proportions summing to 100%. "
                f"This visual instantly reveals segment dominance and market concentration."
            )
        elif chart_type == "box":
            return (
                f"**Why this chart:** {rationale}\n\n"
                f"**Interpretation Guide:** Displays statistical five-number summaries (minimum, 25th percentile, "
                f"median, 75th percentile, maximum) per category. Isolated points past whiskers represent verified statistical outliers."
            )
        elif chart_type == "line":
            return (
                f"**Why this chart:** {rationale}\n\n"
                f"**Interpretation Guide:** Connects continuous observations chronologically along `{x}`. "
                f"Useful for identifying upward/downward momentum, seasonality cycles, and inflection shocks."
            )
        else:
            return f"**Why this chart:** {rationale}\n\n**Interpretation Guide:** Displays relational properties of `{x}`."

    def detect_important_patterns(self, df: pd.DataFrame, rec: Dict[str, Any]) -> List[str]:
        """Detects key empirical patterns, statistical relationships, outliers, and segment leaders."""
        patterns: List[str] = []
        if not rec or rec.get("chart_type") == "none" or df is None or df.empty:
            return ["No significant patterns detected."]
        chart_type = rec.get("chart_type", "distribution")
        x = rec.get("col_x")
        y = rec.get("col_y")

        if chart_type == "correlation_heatmap":
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(num_cols) >= 2:
                corr = df[num_cols].corr().abs()
                np.fill_diagonal(corr.values, 0)
                max_corr = corr.max().max()
                patterns.append(f"**Max Collinearity**: Peak feature correlation in matrix is |r| = {max_corr:.2f}.")
            return patterns or ["Feature collinearity heatmap computed across continuous variables."]

        if not x or x not in df.columns:
            return ["No significant patterns detected due to missing columns."]

        # 1. Scatter Plot Correlation Patterns
        if chart_type == "scatter" and y and y in df.columns:
            clean_s = df[[x, y]].dropna()
            if len(clean_s) > 2:
                r = clean_s[x].corr(clean_s[y])
                if pd.notna(r):
                    strength = "strong" if abs(r) >= 0.7 else ("moderate" if abs(r) >= 0.4 else "weak")
                    direction = "positive" if r > 0 else "negative"
                    r2 = (r ** 2) * 100
                    patterns.append(f"**Correlation Strength**: {strength.title()} {direction} linear relationship (r = {r:.3f}, R² = {r2:.1f}% variance explained).")

                # Detect Outliers via 1.5 * IQR
                q25_x, q75_x = clean_s[x].quantile([0.25, 0.75])
                iqr_x = q75_x - q25_x
                outliers_x = clean_s[(clean_s[x] < q25_x - 1.5 * iqr_x) | (clean_s[x] > q75_x + 1.5 * iqr_x)]
                if len(outliers_x) > 0:
                    pct = (len(outliers_x) / len(clean_s)) * 100
                    patterns.append(f"**Anomalies**: {len(outliers_x):,} data points ({pct:.1f}%) lie outside 1.5× IQR boundary on {x}.")

        # 2. Distribution Patterns
        elif chart_type == "distribution":
            clean_col = df[x].dropna()
            if len(clean_col) > 0 and pd.api.types.is_numeric_dtype(clean_col):
                skew = clean_col.skew()
                mean_val = clean_col.mean()
                median_val = clean_col.median()
                if abs(skew) < 0.5:
                    shape = "symmetric / approximately normal"
                elif skew > 0:
                    shape = f"right-skewed (mean {mean_val:,.1f} > median {median_val:,.1f})"
                else:
                    shape = f"left-skewed (mean {mean_val:,.1f} < median {median_val:,.1f})"
                patterns.append(f"**Distribution Shape**: {shape.title()} with skewness index of {skew:.2f}.")

                q25, q75 = clean_col.quantile([0.25, 0.75])
                iqr = q75 - q25
                outliers = clean_col[(clean_col < q25 - 1.5 * iqr) | (clean_col > q75 + 1.5 * iqr)]
                if len(outliers) > 0:
                    patterns.append(f"**Dispersion & Outliers**: {len(outliers):,} records ({len(outliers)/len(clean_col)*100:.1f}%) exhibit anomalous extreme values outside [{q25 - 1.5*iqr:.1f}, {q75 + 1.5*iqr:.1f}].")
                else:
                    patterns.append(f"**Dispersion**: Stable IQR spread across [{q25:,.1f}, {q75:,.1f}] with zero extreme outliers.")

        # 3. Categorical Patterns
        elif chart_type in ["donut", "horizontal_bar"]:
            vc = df[x].value_counts(normalize=True)
            if len(vc) > 0:
                top_cat = vc.index[0]
                top_pct = vc.iloc[0] * 100
                patterns.append(f"**Segment Dominance**: Leader '{top_cat}' constitutes **{top_pct:.1f}%** of all entries.")
                if len(vc) > 1:
                    ratio = vc.iloc[0] / max(vc.iloc[-1], 0.0001)
                    patterns.append(f"**Concentration Ratio**: Top segment is **{ratio:.1f}×** larger than the lowest segment ('{vc.index[-1]}').")

        # 4. Bar / Box Comparison Patterns
        elif chart_type in ["bar", "box"] and y and y in df.columns:
            grp = df.groupby(x, dropna=False)[y].mean().sort_values(ascending=False)
            if len(grp) >= 2:
                top_name, top_val = grp.index[0], grp.iloc[0]
                bot_name, bot_val = grp.index[-1], grp.iloc[-1]
                delta_pct = ((top_val - bot_val) / max(abs(bot_val), 0.0001)) * 100
                patterns.append(f"**Segment Disparity**: '{top_name}' leads with average {top_val:,.2f}, outperforming '{bot_name}' ({bot_val:,.2f}) by **+{delta_pct:.1f}%**.")

        if not patterns:
            patterns.append(f"**Summary**: Clean observable variance across `{x}` with {df[x].nunique()} unique levels.")

        return patterns

    @staticmethod
    def _create_empty_or_error_result(query: str, message: str, title: str = "Visualization Unavailable", status: str = "error") -> Dict[str, Any]:
        return {
            "status": status,
            "mode": "error",
            "query": query or "",
            "title": title,
            "chart_type": "none",
            "chart_type_label": "None",
            "matched_columns": [],
            "relevant_columns": [],
            "intent": "general",
            "col_x": None,
            "col_y": None,
            "rationale": message,
            "figure": None,
            "explanation": message,
            "patterns": [],
            "collection": [],
            "summary": message,
            "message": message
        }

    def recommend_from_query(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        End-to-end recommendation workflow:
        1. Identify relevant columns & intent
        2. If 'best_collection' requested -> generate multi-chart collection
        3. Select optimal chart
        4. Render Plotly figure
        5. Formulate AI explanation
        6. Compute empirical patterns
        """
        if df is None or df.empty or len(df.columns) == 0:
            return self._create_empty_or_error_result(
                query=query,
                message="Active dataset is empty. Please upload or load a dataset first.",
                title="Active Dataset is Empty"
            )

        matched_cols, intent, meta = self.identify_columns(query, df)

        # Multi-chart collection intent
        if intent == "best_collection":
            collection = self.create_best_charts_collection(df)
            first_item = collection[0] if collection else {}
            first_title = first_item.get("title", f"Curated Visual Suite ({len(collection)} Charts)")
            all_cols = list(dict.fromkeys([col for item in collection for col in item.get("columns", [])]))
            return {
                "status": "success",
                "mode": "collection",
                "query": query,
                "title": f"Curated Visual Suite: {first_title}" if len(collection) == 1 else f"Curated Visualizations Suite ({len(collection)} Charts)",
                "chart_type": first_item.get("chart_type", "collection"),
                "chart_type_label": first_item.get("chart_type_label", "Multi-Chart Suite"),
                "matched_columns": all_cols,
                "relevant_columns": all_cols,
                "intent": "best_collection",
                "col_x": first_item.get("col_x"),
                "col_y": first_item.get("col_y"),
                "rationale": first_item.get("rationale", "Curated visual suite profiling dataset distributions, correlations, and segments."),
                "figure": first_item.get("figure"),
                "explanation": first_item.get("explanation", f"Generated {len(collection)} prioritized charts based on comprehensive dataset profiling."),
                "patterns": first_item.get("patterns", [f"Curated suite contains {len(collection)} charts."]),
                "collection": collection,
                "summary": f"Synthesized {len(collection)} high-impact visualizations profiling the dataset."
            }

        # Single recommended visualization
        try:
            rec = self.recommend_chart_type(df, matched_cols, intent)
            fig = self.generate_visualization(df, rec)
            explanation = self.generate_explanation(df, rec)
            patterns = self.detect_important_patterns(df, rec)
            chart_label = CHART_LABELS.get(rec.get("chart_type", "custom"), str(rec.get("chart_type", "Custom")).capitalize())
            chart_title = rec.get("title") or (f"{chart_label} of {', '.join(matched_cols)}" if matched_cols else "Recommended Visualization")

            return {
                "status": "success",
                "mode": "single",
                "query": query,
                "matched_columns": matched_cols,
                "relevant_columns": matched_cols,
                "intent": intent,
                "chart_type": rec.get("chart_type", "custom"),
                "chart_type_label": chart_label,
                "col_x": rec.get("col_x"),
                "col_y": rec.get("col_y"),
                "title": chart_title,
                "rationale": rec.get("rationale", f"A {chart_label.lower()} is recommended based on feature datatypes."),
                "figure": fig,
                "explanation": explanation,
                "patterns": patterns,
                "collection": [],
                "summary": f"Recommended {chart_label}: {chart_title}"
            }
        except Exception as e:
            return self._create_empty_or_error_result(
                query=query,
                message=f"Could not formulate visualization recommendation: {str(e)}",
                title="Recommendation Error"
            )

    def recommend_chart(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Universal entrypoint accepting either (df, query) or (query, df).
        """
        df = None
        query = ""
        if len(args) == 2:
            if isinstance(args[0], pd.DataFrame):
                df, query = args[0], str(args[1])
            else:
                query, df = str(args[0]), args[1]
        elif len(args) == 1:
            if isinstance(args[0], pd.DataFrame):
                df = args[0]
            else:
                query = str(args[0])
        
        if "df" in kwargs:
            df = kwargs["df"]
        if "query" in kwargs:
            query = kwargs["query"]

        return self.recommend_from_query(query, df)

    def create_best_charts_collection(self, df: pd.DataFrame, max_charts: int = 5) -> List[Dict[str, Any]]:
        """
        Automatically analyzes all columns, detects top correlations, high variance distributions,
        categorical breakups, and temporal trends to generate a curated collection of useful visualizations.
        """
        if df is None or df.empty:
            return []

        collection: List[Dict[str, Any]] = []
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
        date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c]) or any(k in c.lower() for k in ["date", "time", "year"])]

        # 1. Key Metric Distribution (Highest variance / most dispersed numeric feature)
        if num_cols:
            variances = {c: df[c].var() for c in num_cols if pd.notna(df[c].var())}
            top_num = max(variances, key=variances.get) if variances else num_cols[0]
            rec_dist = {
                "chart_type": "distribution",
                "col_x": top_num,
                "title": f"Distribution Profile: {top_num}",
                "rationale": f"Histogram + Boxplot identifies central tendency, skewness, and outliers in primary metric '{top_num}'."
            }
            fig_dist = self.generate_visualization(df, rec_dist)
            collection.append({
                "title": rec_dist.get("title", "Distribution Profile"),
                "chart_type": "distribution",
                "chart_type_label": CHART_LABELS.get("distribution", "Distribution"),
                "intent": "distribution",
                "columns": [top_num],
                "col_x": top_num,
                "col_y": None,
                "rationale": rec_dist.get("rationale", ""),
                "figure": fig_dist,
                "explanation": self.generate_explanation(df, rec_dist),
                "patterns": self.detect_important_patterns(df, rec_dist)
            })

        # 2. Strongest Pairwise Correlation (Scatter Plot with OLS Trendline)
        if len(num_cols) >= 2:
            c1, c2 = self._find_highest_correlated_pair(df, num_cols)
            rec_corr = {
                "chart_type": "scatter",
                "col_x": c1,
                "col_y": c2,
                "title": f"Key Driver Correlation: {c1} vs {c2}",
                "rationale": f"Scatter plot with OLS trendline reveals strongest inter-metric dependency between '{c1}' and '{c2}'."
            }
            fig_corr = self.generate_visualization(df, rec_corr)
            collection.append({
                "title": rec_corr.get("title", f"Correlation: {c1} vs {c2}"),
                "chart_type": "scatter",
                "chart_type_label": CHART_LABELS.get("scatter", "Scatter Plot"),
                "intent": "correlation",
                "columns": [c1, c2],
                "col_x": c1,
                "col_y": c2,
                "rationale": rec_corr.get("rationale", ""),
                "figure": fig_corr,
                "explanation": self.generate_explanation(df, rec_corr),
                "patterns": self.detect_important_patterns(df, rec_corr)
            })

        # 3. Primary Categorical Composition (Donut or Horizontal Bar)
        if cat_cols:
            # Pick categorical column with best cardinality (between 2 and 10)
            best_cat = next((c for c in cat_cols if 2 <= df[c].nunique() <= 10), cat_cols[0])
            n_u = df[best_cat].nunique()
            chart_t = "donut" if n_u <= 6 else "horizontal_bar"
            rec_cat = {
                "chart_type": chart_t,
                "col_x": best_cat,
                "col_y": None,
                "title": f"Segment Breakdown: {best_cat}",
                "rationale": f"{'Donut chart' if chart_t == 'donut' else 'Ranked bar chart'} highlights proportional segment distribution of '{best_cat}'."
            }
            fig_cat = self.generate_visualization(df, rec_cat)
            collection.append({
                "title": rec_cat.get("title", f"Segment Breakdown: {best_cat}"),
                "chart_type": chart_t,
                "chart_type_label": CHART_LABELS.get(chart_t, chart_t.capitalize()),
                "intent": "composition",
                "columns": [best_cat],
                "col_x": best_cat,
                "col_y": None,
                "rationale": rec_cat.get("rationale", ""),
                "figure": fig_cat,
                "explanation": self.generate_explanation(df, rec_cat),
                "patterns": self.detect_important_patterns(df, rec_cat)
            })

        # 4. Bivariate Segment Comparison (Categorical vs Primary Numeric)
        if cat_cols and num_cols:
            cat_c = cat_cols[0]
            num_c = num_cols[0]
            rec_biv = {
                "chart_type": "box" if df[cat_c].nunique() > 5 else "bar",
                "col_x": cat_c,
                "col_y": num_c,
                "title": f"{num_c} by {cat_c} Cohorts",
                "rationale": f"Compares metric variance and averages of '{num_c}' across '{cat_c}' categories."
            }
            fig_biv = self.generate_visualization(df, rec_biv)
            collection.append({
                "title": rec_biv.get("title", f"{num_c} by {cat_c}"),
                "chart_type": rec_biv["chart_type"],
                "chart_type_label": CHART_LABELS.get(rec_biv["chart_type"], rec_biv["chart_type"].capitalize()),
                "intent": "comparison",
                "columns": [cat_c, num_c],
                "col_x": cat_c,
                "col_y": num_c,
                "rationale": rec_biv.get("rationale", ""),
                "figure": fig_biv,
                "explanation": self.generate_explanation(df, rec_biv),
                "patterns": self.detect_important_patterns(df, rec_biv)
            })

        # 5. Temporal Trend (if Date present) OR Correlation Heatmap (if >= 3 numeric)
        if date_cols and num_cols:
            d_col = date_cols[0]
            val_col = num_cols[0]
            rec_time = {
                "chart_type": "line",
                "col_x": d_col,
                "col_y": val_col,
                "title": f"Historical Momentum: {val_col} over {d_col}",
                "rationale": f"Time series line chart tracks growth momentum and historical trajectory of '{val_col}'."
            }
            fig_time = self.generate_visualization(df, rec_time)
            collection.append({
                "title": rec_time.get("title", f"Trend: {val_col}"),
                "chart_type": "line",
                "chart_type_label": CHART_LABELS.get("line", "Line Chart"),
                "intent": "trend",
                "columns": [d_col, val_col],
                "col_x": d_col,
                "col_y": val_col,
                "rationale": rec_time.get("rationale", ""),
                "figure": fig_time,
                "explanation": self.generate_explanation(df, rec_time),
                "patterns": self.detect_important_patterns(df, rec_time)
            })
        elif len(num_cols) >= 3:
            rec_heat = {
                "chart_type": "correlation_heatmap",
                "col_x": None,
                "col_y": None,
                "title": "Comprehensive Feature Collinearity Heatmap",
                "rationale": "Symmetric Pearson correlation heatmap highlights collinear clusters and multi-variable coupling across all continuous attributes."
            }
            fig_heat = self.generate_visualization(df, rec_heat)
            collection.append({
                "title": rec_heat.get("title", "Feature Collinearity Heatmap"),
                "chart_type": "correlation_heatmap",
                "chart_type_label": CHART_LABELS.get("correlation_heatmap", "Heatmap"),
                "intent": "correlation",
                "columns": num_cols,
                "col_x": None,
                "col_y": None,
                "rationale": rec_heat.get("rationale", ""),
                "figure": fig_heat,
                "explanation": self.generate_explanation(df, rec_heat),
                "patterns": self.detect_important_patterns(df, rec_heat)
            })

        return collection[:max_charts]


# Global singleton
default_chart_recommender = AIChartRecommender()
