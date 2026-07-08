from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


def render(name: str, **kwargs) -> str:
    """Load prompts/<name>.txt and .format() it with the given kwargs."""
    template = (_PROMPTS_DIR / f"{name}.txt").read_text().strip()
    return template.format(**kwargs)
