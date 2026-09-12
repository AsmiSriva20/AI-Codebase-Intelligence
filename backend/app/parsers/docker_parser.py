"""Static Dockerfile and Compose analysis; never executes build instructions."""
import re
import shlex
from pathlib import Path

import yaml

from app.parsers.base import empty_analysis


_INSTRUCTION = re.compile(r"^\s*([A-Za-z]+)\s+(.*)$", re.DOTALL)
_HEREDOC = re.compile(r"<<(-?)(?:'([^']+)'|\"([^\"]+)\"|([\w.-]+))")


def language_for_path(path):
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1].lower()
    if (name in {"dockerfile", "containerfile"}
            or name.startswith(("dockerfile.", "containerfile."))
            or name.endswith((".dockerfile", ".containerfile"))):
        return "dockerfile"
    if re.fullmatch(r"(?:docker-)?compose(?:\.[^.]+)*\.ya?ml", name):
        return "docker-compose"
    return None


def _read(path):
    source = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    if "\x00" in source:
        raise ValueError("Binary content is not a Docker configuration")
    return source


def _heredocs(value):
    """Find unquoted shell redirections, excluding strings and here-strings."""
    index = 0
    quote = None
    while index < len(value):
        char = value[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote:
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif value.startswith("<<<", index):
            index += 3
            continue
        elif match := _HEREDOC.match(value, index):
            yield match
            index = match.end()
            continue
        index += 1


def _instructions(source):
    """Keep physical source spans while joining continuations and heredocs."""
    lines = source.splitlines()
    escape = "\\"
    index = 0
    directives_allowed = True
    while index < len(lines):
        start = index
        line = lines[index]
        index += 1
        if directives_allowed:
            directive = re.fullmatch(r"\s*#\s*escape\s*=\s*([\\`])\s*", line, re.I)
            if directive:
                escape = directive.group(1)
            elif not re.match(r"\s*#\s*(syntax|check)\s*=", line, re.I):
                directives_allowed = False
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = []
        while True:
            continued = line.rstrip().endswith(escape)
            parts.append(line.rstrip()[:-1] if continued else line)
            if not continued or index >= len(lines):
                break
            line = lines[index]
            index += 1
            while (not line.strip() or line.lstrip().startswith("#")) and index < len(lines):
                line = lines[index]
                index += 1
        match = _INSTRUCTION.match(" ".join(parts))
        if not match:
            continue
        instruction, value = match.groups()
        instruction = instruction.upper()
        # Heredoc bodies are opaque shell/file content, including lines that
        # happen to start with FROM, COPY, or another Docker instruction.
        if instruction in {"RUN", "COPY", "ADD"}:
            for marker in _heredocs(value):
                delimiter = next(group for group in marker.groups()[1:] if group is not None)
                while index < len(lines):
                    body_line = lines[index]
                    index += 1
                    if (body_line.lstrip("\t") if marker.group(1) else body_line) == delimiter:
                        break
        yield {
            "instruction": instruction, "value": value.strip(),
            "code": "\n".join(lines[start:index]),
            "start_line": start + 1, "end_line": index,
        }


def analyze_file(path):
    source = _read(path)
    result = empty_analysis()
    result.update(raw_text=source, blocks=[], instructions=[], stages=[])
    stage_names = set()
    dependencies = []
    for item in _instructions(source):
        result["instructions"].append(item)
        result["blocks"].append({
            **item, "type": "docker_instruction",
            "name": f"{item['instruction']} {item['value'].splitlines()[0] if item['value'] else ''}".rstrip(),
        })
        if item["instruction"] == "FROM":
            try:
                tokens = shlex.split(item["value"])
            except ValueError:
                continue
            tokens = [token for token in tokens if not token.startswith("--")]
            if not tokens:
                continue
            base = tokens[0]
            alias = tokens[2] if len(tokens) >= 3 and tokens[1].upper() == "AS" else None
            result["stages"].append({"base_image": base, "name": alias, "start_line": item["start_line"]})
            if base.lower() not in stage_names and base.lower() != "scratch":
                dependencies.append(base)
            if alias:
                stage_names.add(alias.lower())
        elif item["instruction"] in {"COPY", "ADD"}:
            match = re.search(r"(?:^|\s)--from=(\S+)", item["value"])
            if match:
                reference = match.group(1).strip("\"'")
                if reference.lower() not in stage_names and not reference.isdigit():
                    dependencies.append(reference)
    result["imports"] = list(dict.fromkeys(dependencies))
    return result


def analyze_compose_file(path):
    source = _read(path)
    result = empty_analysis()
    result.update(raw_text=source, blocks=[], services=[])
    try:
        data = yaml.safe_load(source)
        root = yaml.compose(source, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        # Partially edited configuration remains searchable as plain text.
        return result
    if not isinstance(data, dict) or not isinstance(data.get("services"), dict):
        return result
    service_nodes = {}
    if isinstance(root, yaml.MappingNode):
        for key, value in root.value:
            if key.value == "services" and isinstance(value, yaml.MappingNode):
                service_nodes = {key.value: (key, value) for key, value in value.value}
    lines = source.splitlines()
    for name, config in data["services"].items():
        if not isinstance(name, str) or not isinstance(config, dict):
            continue
        depends_on = config.get("depends_on") or []
        dependencies = list(depends_on) if isinstance(depends_on, (list, dict)) else []
        service = {
            "name": name, "image": config.get("image"),
            "build": config.get("build"), "depends_on": dependencies,
            "ports": config.get("ports") or [],
        }
        result["services"].append(service)
        if isinstance(service["image"], str):
            result["imports"].append(service["image"])
        nodes = service_nodes.get(name)
        if nodes:
            key, value = nodes
            start = key.start_mark.line
            # Aliases may point backwards; keep the service's own source line.
            end = max(start + 1, len(source[:value.end_mark.index].rstrip().splitlines()))
            end = min(end, len(lines))
            result["blocks"].append({
                "type": "docker_service", "name": name,
                "code": "\n".join(lines[start:end]),
                "start_line": start + 1, "end_line": end,
            })
    result["imports"] = list(dict.fromkeys(result["imports"]))
    return result


class ComposeParser:
    analyze_file = staticmethod(analyze_compose_file)
