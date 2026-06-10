import os
import json
from litellm import completion

def summarize_context_for_llm(context: dict, enriched_analysis: str = None) -> str:
    """Produces a token-efficient string summary for LLM prompts."""
    topics = context.get('topics', [])
    if not isinstance(topics, list):
        topics = list(topics)
        
    summary = f"""
Project: {context.get('name', 'Unknown')}
Description: {context.get('description', 'No description provided.')}
Language: {context.get('language', 'Unknown')}
Stars: {context.get('stars', 0)}
Topics: {', '.join(topics)}
README (first 1500 chars): {context.get('readme', '')[:1500]}
Key files present: {', '.join(context.get('key_files', {}).keys())}
"""

    if enriched_analysis:
        summary += f"\n--- Enriched Analysis ---\n{enriched_analysis}\n"

    key_file_contents = ""
    for path, content in list(context.get('key_files', {}).items())[:3]:
        key_file_contents += f"\n--- {path} ---\n{content[:500]}\n"
        
    if key_file_contents:
        summary += f"\nFile Samples:{key_file_contents}"
        
    return summary

def analyze_codebase(context: dict) -> dict:
    """Master analysis — what it does, who it's for, key features, tech stack"""
    summary = summarize_context_for_llm(context)
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    
    prompt = f"""
    Analyze the following GitHub repository codebase and metadata.
    Determine:
    1. What problem it solves.
    2. Who the target audience is.
    3. The key features.
    4. The core technology stack.
    
    Repository Data:
    {summary}
    
    Return the response as a JSON object with keys: 'problem_solved', 'target_audience', 'key_features', 'tech_stack'.
    """
    
    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": "You are a code analysis assistant. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error in analyze_codebase: {e}")
        return {}

def generate_readme_content(context: dict, enriched_analysis: dict) -> str:
    """Full README markdown output"""
    summary = summarize_context_for_llm(context, json.dumps(enriched_analysis))
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    
    prompt = f"""
    Write a high-quality, professional README.md for the following repository.
    Include standard sections: Hero/Title, Badges (placeholders), Hook/Introduction, Installation, Usage, and Tech Stack.
    Use the provided enriched analysis to ensure the messaging is spot-on for the target audience.
    
    Repository Data & Analysis:
    {summary}
    
    Return ONLY valid markdown content.
    """
    
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in generate_readme_content: {e}")
        return "Error generating README."

def generate_social_posts(context: dict, platforms: list, enriched_analysis: dict) -> dict:
    """Returns dict of {platform: post_content}"""
    summary = summarize_context_for_llm(context, json.dumps(enriched_analysis))
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    
    prompt = f"""
    Generate social media launch posts for this repository for the following platforms: {', '.join(platforms)}.
    - LinkedIn: Professional, metric-forward, 3 paragraphs, hashtags.
    - Twitter/X: 5-tweet thread, hook -> problem -> solution -> stack -> CTA.
    - Dev.to: Title, subheadings, intro paragraph for an article.
    
    Repository Data & Analysis:
    {summary}
    
    Return the response as a JSON object where the keys are the platform names (e.g. 'linkedin', 'twitter', 'devto') and the values are the generated text.
    """
    
    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": "You are a social media copywriter. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error in generate_social_posts: {e}")
        return {}
