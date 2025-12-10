import json
import requests
from django.conf import settings


class GroqError(Exception):
    pass


def call_groq(prompt: str, model: str = 'groq-mini', max_tokens: int = 256) -> dict:
    """
    Minimal wrapper to call a Groq-style completion API.

    Notes:
    - The exact request shape may vary depending on Groq API version; this wrapper
      uses a common completion payload with `model` and `prompt` fields. If your
      Groq API requires a different shape, set `GROQ_API_URL` accordingly.
    - Provide your API key via the `GROQ_API_KEY` environment variable (or in
      Django settings).
    """
    key = getattr(settings, 'GROQ_API_KEY', None)
    url = getattr(settings, 'GROQ_API_URL', None)
    if not key:
        raise GroqError('GROQ_API_KEY not configured')
    if not url:
        raise GroqError('GROQ_API_URL not configured')

    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }

    payload = {
        'model': model,
        'prompt': prompt,
        'max_tokens': max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise GroqError(f'HTTP error calling Groq API: {e}')

    try:
        return resp.json()
    except Exception:
        raise GroqError('Failed to parse Groq response as JSON')


def classify_specialization(problem_text: str) -> str:
    """Ask Groq to map a short symptom text to one of the known specializations.

    Returns the specialization string if confident, otherwise returns empty string.
    """
    prompt = (
        "You are a hospital assistant. Map the following short patient problem to one "
        "of these specializations: Cardiology, Orthopedics, General Medicine, Dermatology, "
        "ENT, Gynecology, Pediatrics. Reply with only the specialization name.\n\n"
        f"Problem: {problem_text}\n\nSpecialization:"
    )
    try:
        data = call_groq(prompt, model='groq-mini', max_tokens=16)
    except GroqError:
        return ''

    # Try a few common response shapes
    text = ''
    if isinstance(data, dict):
        # common providers return {'choices':[{'text': '...'}]} or {'output': '...'}
        if 'choices' in data and isinstance(data['choices'], list) and data['choices']:
            text = data['choices'][0].get('text', '')
        elif 'output' in data:
            if isinstance(data['output'], list):
                # some Groq SDKs return list of tokens
                text = ' '.join(map(str, data['output']))
            else:
                text = str(data['output'])
        else:
            # fallback to raw string conversion
            text = str(data)
    else:
        text = str(data)

    text = text.strip().split('\n')[0]
    # normalize
    text = text.strip().lower()
    if 'cardio' in text:
        return 'Cardiology'
    if 'ortho' in text:
        return 'Orthopedics'
    if 'derm' in text:
        return 'Dermatology'
    if 'ent' in text:
        return 'ENT'
    if 'gyn' in text or 'women' in text:
        return 'Gynecology'
    if 'pedi' in text or 'child' in text:
        return 'Pediatrics'
    if 'general' in text or 'medicine' in text:
        return 'General Medicine'
    return ''
