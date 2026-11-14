"""Configurable JSON-over-HTTP inference for the MutationScientist report."""

import json
import os
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ModelError(RuntimeError):
    """The configured model could not return a usable response."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configured_model():
    """Return a generation callable and its model ID, or (None, None)."""
    url = os.getenv("MUTATIONSCIENTIST_LLM_URL")
    model = os.getenv("MUTATIONSCIENTIST_LLM_MODEL")
    if not url and not model:
        return None, None
    if not url or not model:
        raise ValueError("Set both MUTATIONSCIENTIST_LLM_URL and MUTATIONSCIENTIST_LLM_MODEL.")
    endpoint = urlsplit(url)
    if endpoint.scheme != "https" and not (
        endpoint.scheme == "http" and endpoint.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("Use an HTTPS model endpoint or a local HTTP endpoint.")
    if not endpoint.hostname or endpoint.username or endpoint.password or endpoint.fragment:
        raise ValueError("Use a model endpoint URL with a host and without credentials or a fragment.")
    protocol = os.getenv("MUTATIONSCIENTIST_LLM_PROTOCOL", "chat")
    if protocol not in {"chat", "responses"}:
        raise ValueError("MUTATIONSCIENTIST_LLM_PROTOCOL must be chat or responses.")
    key = os.getenv("MUTATIONSCIENTIST_LLM_API_KEY")
    opener = build_opener(NoRedirects())

    def generate(messages):
        body = {"model": model, "stream": False}
        if protocol == "chat":
            body.update(messages=messages, max_tokens=512)
        else:
            body.update(input=messages, max_output_tokens=512, store=False, tool_choice="none")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if key:
            headers["Authorization"] = "Bearer " + key
        request = Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with opener.open(request, timeout=30) as response:
                data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise ValueError("Model response exceeds the size limit.")
            payload = json.loads(data)
            if protocol == "chat":
                text = payload["choices"][0]["message"]["content"]
            else:
                text = "".join(
                    block["text"]
                    for item in payload["output"] if item["type"] == "message"
                    for block in item["content"] if block["type"] == "output_text"
                )
        except (URLError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelError("The configured model endpoint did not return a valid answer.") from exc
        if not isinstance(text, str) or not text.strip():
            raise ModelError("The configured model returned an empty answer.")
        return text

    return generate, model
