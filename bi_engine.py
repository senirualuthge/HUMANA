import json
from openai import OpenAI # type: ignore
import os

# Lazy initialization — client is created on first use so import
# succeeds even when OPENAI_API_KEY is not set.
_openai_client = None

def _get_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

DASHBOARD_SYSTEM_PROMPT = """
You are an expert data dashboard architect.
Generate a dashboard configuration JSON based on the user's description.
The dashboard must contain KPI metrics, charts, tables, and a layout grid.
Return ONLY valid JSON.

Use this schema:
{
 "dashboard_name": "string",
 "layout": {
   "columns": 12
 },
 "components": [
  {
   "id": "string",
   "type": "kpi_card | line_chart | bar_chart | pie_chart | table",
   "title": "string",
   "data_source": "string",
   "position": {"x": 0, "y": 0, "w": 3, "h": 1},
   "config": {}
  }
 ]
}
"""

def ai_generate_dashboard(prompt: str) -> dict:
    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": DASHBOARD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error generating dashboard: {e}")
        # Return a fallback simple dashboard
        return {
            "dashboard_name": "Fallback Required Dashboard",
            "layout": {"columns": 12},
            "components": [
                {
                    "id": "kpi_fallback",
                    "type": "kpi_card",
                    "title": "Data Connection Failed",
                    "data_source": "metrics.placeholder",
                    "position": {"x": 0, "y": 0, "w": 3, "h": 1},
                    "config": {}
                }
            ]
        }

INSIGHT_SYSTEM_PROMPT = """
You are a business intelligence AI.
Analyze these metrics and identify:
1) anomalies
2) risks
3) revenue opportunities
4) operational inefficiencies
Return actionable insights as a strict JSON list inside an "insights" key.
Each insight MUST have:
- type: 'opportunity', 'anomaly', or 'recommendation'
- severity: 'high', 'medium', or 'low'
- message: A clear sentence describing the finding
- causes: A list of string causes
- confidence: A float between 0.0 and 1.0

Example JSON:
{
 "insights": [
   {
     "type": "opportunity",
     "severity": "high",
     "message": "Customers ask about delivery frequently. Adding shipping calculator could increase conversion.",
     "causes": ["Chat logic frequently hands off shipping queries"],
     "confidence": 0.88
   }
 ]
}
"""

def ai_generate_insights(metrics_summary: str) -> list:
    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze these metrics:\n{metrics_summary}"}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("insights", [])
    except Exception as e:
        print(f"Error generating insights: {e}")
        return []

def generate_admin_insight(prompt: str) -> str:
    """Proxy generic text prompts from the admin dashboard to GPT-4o."""
    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant for a business platform administrator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"Error proxying admin AI: {e}")
        return "An error occurred generating the insight. Please check server logs."
