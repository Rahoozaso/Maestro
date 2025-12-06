from django.conf import settings
from django.core.checks import Error, Tags, register
from django.utils.translation import get_supported_language_variant


@register(Tags.translation)
def check_setting_languages(app_configs, **kwargs):
    """Check for a pre-1.8 global LANGUAGES setting."""
    if hasattr(settings, 'LANGUAGES') and not isinstance(settings.LANGUAGES, (list, tuple)):
        return [
            Error(
                "The LANGUAGES setting must be a list or a tuple.",
                id='translation.E001',
            )
        ]
    return []


@register(Tags.translation)
def check_language_settings_consistent(app_configs, **kwargs):
    """Check consistency of language related settings."""
    errors = []
    if (settings.USE_I18N is False and settings.USE_L10N is True) or (
        settings.USE_I18N is False and settings.USE_TZ is True
    ):
        errors.append(
            Error(
                'You have enabled localization (USE_L10N) or time zone support '
                '(USE_TZ), but USE_I18N is set to False. These settings require '
                'USE_I18N to be True.',
                id='translation.E002',
            )
        )
    if settings.USE_I18N and not settings.LANGUAGES:
        errors.append(
            Error(
                "You have enabled internationalization (USE_I18N) but the "
                "LANGUAGES setting is empty.",
                id='translation.E003',
            )
        )
    return errors


@register(Tags.translation)
def check_language_code(app_configs, **kwargs):
    """Validate settings.LANGUAGE_CODE against settings.LANGUAGES.

    This mirrors Django's documented behavior where a requested sublanguage
    (e.g. "de-at") may fall back to an available base language (e.g. "de").
    In such a case, translation.E004 must not be raised.
    """
    errors = []
    language_code = settings.LANGUAGE_CODE

    # If LANGUAGES is not defined or empty, other checks cover this scenario;
    # here we only validate when there is a non-empty languages list.
    languages = getattr(settings, 'LANGUAGES', None) or []
    language_codes = {code for code, _ in languages}

    # Exact match in LANGUAGES is always valid.
    if language_code in language_codes:
        return errors

    # Attempt to resolve LANGUAGE_CODE using Django's supported language
    # resolution, which implements fallback from sublanguages to base
    # languages when possible.
    resolved = None
    try:
        resolved = get_supported_language_variant(language_code, strict=False)
    except LookupError:
        resolved = None

    # If resolution succeeded and the resolved code is one of LANGUAGES,
    # treat LANGUAGE_CODE as valid and do not raise E004.
    if resolved is not None and resolved in language_codes:
        return errors

    # No matching language or fallback found in LANGUAGES: raise E004.
    errors.append(
        Error(
            'You have provided a value for the LANGUAGE_CODE setting that is not in the LANGUAGES setting.',
            id='translation.E004',
        )
    )
    return errors