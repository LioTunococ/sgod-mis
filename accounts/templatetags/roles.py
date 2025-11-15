from __future__ import annotations

from django import template

from accounts import roles

register = template.Library()


@register.simple_tag
def is_school_head(user):
    return roles.is_school_head(user)


@register.simple_tag
def is_psds(user):
    return roles.is_psds(user)


@register.simple_tag
def is_section_admin(user, section_code=None):
    return roles.is_section_admin(user, section_code)


@register.simple_tag
def is_sgod_admin(user):
    return roles.is_sgod_admin(user)
