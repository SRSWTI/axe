from pathlib import Path
from axe_cli.config import load_config
import os

def debug_anthropic_config():
    print("Loading axe config...")
    # Load from default location (~/.axe/config.toml)
    config = load_config()
    
    if "anthropic" in config.providers:
        prov = config.providers["anthropic"]
        print(f"Provider Type: {prov.type}")
        print(f"Base URL: '{prov.base_url}'")
        key = prov.api_key.get_secret_value() if prov.api_key else "None"
        print(f"API Key Length: {len(key)}")
        print(f"API Key Starts With: {key[:20]}...")
        print(f"API Key Ends With: ...{key[-20:]}")
        # explicit check for whitespace
        if key.strip() != key:
            print("WARNING: API Key has leading/trailing whitespace!")
        else:
            print("API Key has no leading/trailing whitespace.")
            
    else:
        print("Anthropic provider not found in config.")

    if "claude-4-5-sonnet" in config.models:
        mod = config.models["claude-4-5-sonnet"]
        print(f"Model ID: '{mod.model}'")
        print(f"Model Provider: '{mod.provider}'")
    else:
        print("claude-4-5-sonnet model config not found.")

if __name__ == "__main__":
    debug_anthropic_config()
