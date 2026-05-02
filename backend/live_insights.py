"""Live meeting data extraction and visualization service."""
import re
import json
import logging
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_live_data(text_chunk: str) -> dict:
    """Extract business metrics and data from live meeting text."""
    
    # Quick regex patterns for common metrics
    patterns = {
        'sales': r'sales?\s*(?:was|is|hai|tha)?\s*(?:rs\.?|rupees?)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|crore|thousand|k|million)?',
        'revenue': r'revenue\s*(?:was|is|hai|tha)?\s*(?:rs\.?|rupees?)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|crore|thousand|k|million)?',
        'growth': r'growth\s*(?:is|hai|hua)?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)',
        'budget': r'budget\s*(?:is|hai)?\s*(?:rs\.?|rupees?)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|crore|thousand|k|million)?',
        'profit': r'profit\s*(?:is|hai)?\s*(?:rs\.?|rupees?)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|crore|thousand|k|million)?',
        'tasks': r'(\w+)\s*(?:completed|complete|kiye)\s*(\d+)\s*tasks?',
        'efficiency': r'(\w+)(?:\'s|ka)?\s*efficiency\s*(?:is|hai)?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?'
    }
    
    extracted_data = {}
    
    # Extract using patterns
    for metric, pattern in patterns.items():
        matches = re.findall(pattern, text_chunk.lower())
        if matches:
            extracted_data[metric] = matches
    
    # If significant data found, use AI for better extraction
    if extracted_data or any(keyword in text_chunk.lower() for keyword in ['sales', 'revenue', 'growth', 'profit', 'budget', 'performance']):
        ai_data = extract_with_ai(text_chunk)
        if ai_data:
            extracted_data.update(ai_data)
    
    return extracted_data

def extract_with_ai(text: str) -> dict:
    """Use AI to extract structured business data from meeting text."""
    
    prompt = f"""Extract business metrics and data from this meeting text. Return ONLY valid JSON.

Text: "{text}"

Extract any mentioned:
- Sales figures (current, previous, growth)
- Revenue data
- Budget information  
- Team performance (names, tasks, efficiency)
- Profit/loss data
- Growth percentages
- Comparisons (this vs last month/quarter)

Return JSON format:
{{
    "metrics": [
        {{
            "type": "sales|revenue|growth|budget|profit|performance",
            "current_value": number,
            "previous_value": number (if mentioned),
            "unit": "lakh|crore|percent|tasks",
            "person": "name (if person-specific)",
            "context": "brief description"
        }}
    ],
    "chart_type": "bar|line|pie|comparison",
    "title": "Chart title"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        
        text_response = response.choices[0].message.content.strip()
        
        # Clean JSON
        if "```json" in text_response:
            text_response = text_response.split("```json")[1].split("```")[0].strip()
        elif "```" in text_response:
            text_response = text_response.split("```")[1].split("```")[0].strip()
        
        return json.loads(text_response)
        
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return {}

def generate_chart_config(data: dict) -> dict:
    """Generate Chart.js configuration from extracted data."""
    
    if not data or 'metrics' not in data:
        return {}
    
    metrics = data['metrics']
    chart_type = data.get('chart_type', 'bar')
    title = data.get('title', 'Meeting Insights')
    
    # Generate chart based on data type
    if chart_type == 'comparison' and len(metrics) > 0:
        metric = metrics[0]
        if metric.get('previous_value') and metric.get('current_value'):
            return {
                "type": "bar",
                "data": {
                    "labels": ["Previous", "Current"],
                    "datasets": [{
                        "label": metric.get('type', 'Value').title(),
                        "data": [metric['previous_value'], metric['current_value']],
                        "backgroundColor": ["#ff6384", "#36a2eb"],
                        "borderColor": ["#ff6384", "#36a2eb"],
                        "borderWidth": 1
                    }]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": title
                        }
                    },
                    "scales": {
                        "y": {
                            "beginAtZero": True
                        }
                    }
                }
            }
    
    elif chart_type == 'performance' and len(metrics) > 1:
        # Team performance chart
        names = [m.get('person', f'Person {i+1}') for i, m in enumerate(metrics)]
        values = [m.get('current_value', 0) for m in metrics]
        
        return {
            "type": "bar",
            "data": {
                "labels": names,
                "datasets": [{
                    "label": "Performance",
                    "data": values,
                    "backgroundColor": "#4bc0c0",
                    "borderColor": "#4bc0c0",
                    "borderWidth": 1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": title
                    }
                }
            }
        }
    
    # Default single metric chart
    if metrics:
        metric = metrics[0]
        return {
            "type": "doughnut",
            "data": {
                "labels": [metric.get('type', 'Metric').title(), "Remaining"],
                "datasets": [{
                    "data": [metric.get('current_value', 0), 100 - metric.get('current_value', 0)],
                    "backgroundColor": ["#ff6384", "#e0e0e0"]
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": title
                    }
                }
            }
        }
    
    return {}

def should_generate_chart(text: str) -> bool:
    """Check if text contains data worth visualizing."""
    keywords = [
        'sales', 'revenue', 'growth', 'profit', 'budget', 'performance',
        'lakh', 'crore', 'percent', '%', 'tasks', 'efficiency',
        'comparison', 'vs', 'increase', 'decrease', 'badha', 'kam'
    ]
    
    return any(keyword in text.lower() for keyword in keywords) and any(char.isdigit() for char in text)