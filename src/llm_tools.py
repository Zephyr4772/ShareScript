import os
import json
from openai import AzureOpenAI

# Default API version updated to a recent one
DEFAULT_API_VERSION = "2024-05-01-preview"
AZURE_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

_client = None

def get_azure_openai_client() -> AzureOpenAI:
    """
    Initializes the Azure OpenAI client.
    Expects AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_API_VERSION to be set.
    """
    global _client
    if _client is not None:
        return _client
        
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION)
    
    if not endpoint or not api_key:
        print("Warning: Azure OpenAI credentials not found. LLM calls will fail.")
        
    _client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version
    )
    return _client

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
    client = get_azure_openai_client()
    summary = summarize_context_for_llm(context)
    
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
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error in analyze_codebase: {e}")
        return {}

def generate_readme_content(context: dict, enriched_analysis: dict) -> str:
    """Full README markdown output"""
    client = get_azure_openai_client()
    summary = summarize_context_for_llm(context, json.dumps(enriched_analysis))
    
    prompt = f"""
    Write a high-quality, professional README.md for the following repository.
    Include standard sections: Hero/Title, Badges (placeholders), Hook/Introduction, Installation, Usage, and Tech Stack.
    Use the provided enriched analysis to ensure the messaging is spot-on for the target audience.
    
    Repository Data & Analysis:
    {summary}
    
    Return ONLY valid markdown content.
    """
    
    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in generate_readme_content: {e}")
        return "Error generating README."

def generate_social_posts(context: dict, platforms: list, enriched_analysis: dict) -> dict:
    """Returns dict of {platform: post_content}"""
    client = get_azure_openai_client()
    summary = summarize_context_for_llm(context, json.dumps(enriched_analysis))
    
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
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error in generate_social_posts: {e}")
        return {}
