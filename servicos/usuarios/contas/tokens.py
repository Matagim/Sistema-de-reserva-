import time

import jwt
from django.conf import settings


def emitir(usuario):
    
    agora = int(time.time())
    claims = {
        "sub": str(usuario.id),  
        "nome": usuario.nome,
        "email": usuario.email,
        "papel": usuario.papel,
        "iat": agora,
        "exp": agora + settings.JWT_EXPIRA_HORAS * 3600,
    }
    return jwt.encode(claims, settings.JWT_SEGREDO, algorithm="HS256")
