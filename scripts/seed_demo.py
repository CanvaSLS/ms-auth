"""Carga explícita por un operador; no sobreescribe cuentas existentes."""
import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import storage
from auth.security import hash_password
from common import now_iso, validate_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--demo", action="store_true", help="Usar Demo2026!, como frontend-kit (solo laboratorio)")
    args = parser.parse_args()
    # Sin claves ni contraseñas en argumentos, archivos versionados o logs.
    password = "Demo2026!" if args.demo else getpass.getpass("Contraseña (12+ caracteres, mayúscula, minúscula, número): ")
    if not args.demo:
        validate_password(password)
    os.environ["AWS_DEFAULT_REGION"] = args.region
    os.environ["T_USUARIOS"] = "sp_usuarios"
    cast = [("D001", "profe", "Carlos Salas", "docente"),
            ("A00001", "ana.torres", "Ana Torres", "alumno"),
            ("A00003", "valeria.mendoza", "Valeria Mendoza", "alumno"),
            ("X01", "admin", "Administrador Demo", "admin")]
    for tenant, domain in [("UTEC", "utec.edu.pe"), ("NORTE", "inorte.edu.pe"), ("ANDINO", "andino.edu.pe")]:
        for uid, local, nombre, role in cast:
            email = f"{local}@{domain}"
            user = {"tenant_id": tenant, "user_id": uid, "email": email,
                    "nombre": nombre, "rol": role, "estado": "ACTIVO",
                    "created_at": now_iso(), "password_hash": hash_password(password)}
            try:
                if storage.get_by_email(tenant, email):
                    print(f"Ya existe, sin cambios: {tenant} / {email}")
                    continue
                storage.create_user(user)
                print(f"Creado: {tenant} / {email}")
            except Exception as error:
                if not storage.conditional_failure(error):
                    raise
                print(f"Ya existe, sin cambios: {tenant} / {email}")


if __name__ == "__main__":
    main()
