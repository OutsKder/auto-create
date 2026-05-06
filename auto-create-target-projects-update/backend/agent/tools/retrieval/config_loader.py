import json
import os
from typing import Dict, List


def _default_rule_pack() -> Dict[str, Dict[str, List[str]]]:
    return {
        "term_map": {
            "用户": ["user", "users", "auth", "account", "profile", "permission"],
            "邮箱": ["email", "mail", "smtp", "notification", "auth"],
            "登录": ["login", "auth", "token", "session"],
            "权限": ["permission", "role", "acl", "guard"],
        },
        "synonym_map": {
            "user": ["users", "account", "profile"],
            "email": ["mail", "smtp"],
            "auth": ["login", "token", "session"],
        },
        "zh_map": {
            "用户": ["user", "users", "account", "profile"],
            "邮箱": ["email", "mail", "smtp"],
            "登录": ["login", "auth", "token", "session"],
            "权限": ["permission", "role", "acl", "guard"],
        },
    }


def load_rule_pack(name: str = "default") -> Dict[str, Dict[str, List[str]]]:
    """Load rule/synonym config from retrieval/rule_configs/*.json."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "rule_configs", f"{name}.json")

    if not os.path.exists(config_path):
        if name != "default":
            return load_rule_pack("default")
        return _default_rule_pack()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception:
        if name != "default":
            return load_rule_pack("default")
        return _default_rule_pack()

    defaults = _default_rule_pack()
    merged: Dict[str, Dict[str, List[str]]] = {
        "term_map": dict(defaults.get("term_map", {})),
        "synonym_map": dict(defaults.get("synonym_map", {})),
        "zh_map": dict(defaults.get("zh_map", {})),
    }

    for section in ["term_map", "synonym_map", "zh_map"]:
        merged[section].update(loaded.get(section, {}))

    return merged
