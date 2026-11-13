"""Compatibilidad para invocaciones locales del archivo original."""
from auth.handlers.register import handler as registro
from auth.handlers.login import handler as login
from auth.handlers.authorizer import handler as autorizar
from auth.handlers.me import handler as me
from auth.handlers.logout import handler as logout
from auth.handlers.users import handler as listar_usuarios
