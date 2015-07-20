from django import template
from django.utils.safestring import mark_safe

from symposion.markdown_parser import parse

register = template.Library()

@register.filter
def markdown(text):
    return mark_safe(parse(text))
