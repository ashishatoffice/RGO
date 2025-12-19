from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if not dictionary: return None
    return dictionary.get(key)

@register.filter
def get_type(cell):
    if cell and isinstance(cell, dict):
        return cell.get('type')
    return None
