from pathlib import Path


def load_prompt(file_name):
    prompt = (Path("prompts") / file_name).read_text(encoding="UTF-8")
    return prompt
