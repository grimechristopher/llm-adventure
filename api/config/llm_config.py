# config/llm_config.py
"""LLM provider configuration and preferences"""

LLM_PROVIDERS = {
    # Providers registered here by app.py at startup
}

PLUGIN_LLM_PREFERENCES = {
    "conversational": "gpt-4o",
    "autonomous": "gpt-4",
    "data_pipeline": "local-qwen",
}
