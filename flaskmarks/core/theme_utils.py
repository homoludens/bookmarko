"""
Theme utilities for rendering theme-specific templates.
"""
from flask import render_template, g
from jinja2 import TemplateNotFound


def render_themed_template(template_name: str, **context):
    """
    Render a template with theme support.
    
    First tries to load a theme-specific template from themes/<theme_name>/<template_name>,
    falls back to the default template if not found.
    
    Args:
        template_name: The template path (e.g., 'mark/index.html')
        **context: Template context variables
        
    Returns:
        Rendered template string
    """
    user_theme = 'default'
    
    if hasattr(g, 'user') and g.user.is_authenticated:
        user_theme = getattr(g.user, 'theme', 'default') or 'default'
    
    if user_theme != 'default':
        themed_template = f'themes/{user_theme}/{template_name}'
        try:
            return render_template(themed_template, **context)
        except TemplateNotFound:
            pass
    
    return render_template(template_name, **context)
