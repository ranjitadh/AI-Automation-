def parse_structured_response(content: str, schema: dict = None) -> dict:
    import json
    import re

    if not content:
        return {}

    content = content.strip()

    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    try:
        start = content.index('{')
        end = content.rindex('}') + 1
        return json.loads(content[start:end])
    except (ValueError, json.JSONDecodeError):
        return {}
