"""Gestión segura de contraseñas; nunca se guarda texto plano."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

ITERACIONES = 600_000


def generar_hash_contrasena(contrasena: str) -> str:
    if not isinstance(contrasena,str) or not 10 <= len(contrasena) <= 128:
        raise ValueError("La contraseña debe tener entre 10 y 128 caracteres")
    sal = os.urandom(16)
    resumen = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${base64.b64encode(sal).decode()}${base64.b64encode(resumen).decode()}"


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    algoritmo, iteraciones, sal64, resumen64 = hash_guardado.split("$", 3)
    if algoritmo != "pbkdf2_sha256":
        return False
    resumen_actual = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), base64.b64decode(sal64), int(iteraciones))
    return hmac.compare_digest(resumen_actual, base64.b64decode(resumen64))
