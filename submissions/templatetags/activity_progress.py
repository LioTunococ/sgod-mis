from django import template

register = template.Library()

@register.filter
def percent_complete(completed, total):
    try:
        completed = int(completed)
        total = int(total)
        if total == 0:
            return "0"
        return str(int(round(100 * completed / total)))
    except Exception:
        return "0"
