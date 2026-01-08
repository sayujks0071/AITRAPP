"""
Configuration loader.
"""
import yaml
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

def load_instrument_map():
    path = os.path.join(CONFIG_DIR, "instrument_map.yaml")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_foundry_config():
    path = os.path.join(CONFIG_DIR, "foundry.yaml")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)
