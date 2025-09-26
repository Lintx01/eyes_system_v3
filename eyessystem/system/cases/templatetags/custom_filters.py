from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """从字典中获取指定键的值"""
    if dictionary and key:
        return dictionary.get(str(key), '')
    return ''