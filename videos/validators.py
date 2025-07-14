# myapp/validators.py

from django.core.exceptions import ValidationError
from videos.utils import get_tokenizer

import logging

logger = logging.getLogger("django_mcq")


def validate_prompt_token_length(value):
    tokenizer = get_tokenizer()
    token_count = len(tokenizer.encode(value, add_special_tokens=False))
    logger.info(f" token count is equal to {token_count}")
    if token_count > 226:
        raise ValidationError(f"Prompt is too long: {token_count} tokens (max 226)")
