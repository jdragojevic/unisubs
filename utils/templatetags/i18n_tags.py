from django import template
from django.conf import settings
from django.utils.translation import (
    get_language_info, gettext_lazy as _
)

from unilangs import get_language_name_mapping

import logging
logger = logging.getLogger('utils.languagetags')

LANGUAGE_NAMES = get_language_name_mapping('unisubs')
register = template.Library()

@register.filter()
def to_localized_display(language_code):
    '''
    Translates from a language code to the language name
    in the locale the user is viewing the site. For example:
    en -> Anglaise (if user is viewing with 'fr'
    en -> English
    It uses the django internal machinery to figure out what
    language the request cicle is in, currently set on the
    localurl middleware.
    IF anything is wrong, will log the missing error and
    will return a '?'.
    '''
    try:
        return _(get_language_info(unicode(language_code))['name'].encode('utf-8'))
    except KeyError:
        logger.error('Uknown language code to be translated', extra={
            'language_code': unicode(language_code),
        })
    return '?'


@register.filter()
def to_language_display(language_code):
    return  LANGUAGE_NAMES[language_code]
