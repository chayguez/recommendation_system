from django import template
from django.template.defaultfilters import register
# register = template.Library()

# @register.filter(name="get_item")
# def get_item(dictionary, key):
#     return dictionary.get(key, None)

@register.filter(name='dictlookup')
def dictlookup(value, arg):
    try:
        return value.get(arg)
    except AttributeError:
        return None