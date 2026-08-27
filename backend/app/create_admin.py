from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Role, User


def ensure_admin(db, email: str, password: str):
    role = db.scalar(select(Role).where(Role.name == "admin"))

    if not role:
        role = Role(name="admin")
        db.add(role)
        db.flush()

    user = db.scalar(select(User).where(User.email == email))

    if user:
        user.password_hash = hash_password(password)
        user.role_id = role.id
        user.is_active = True
        db.flush()
        return user, False

    user = User(
        email=email,
        password_hash=hash_password(password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user, True


def main():
    if not settings.admin_email or not settings.admin_password:
        raise SystemExit("Configura ADMIN_EMAIL y ADMIN_PASSWORD")

    if settings.is_production and (
        len(settings.admin_password) < 12
        or settings.admin_password == "KittyBoom123!"
    ):
        raise SystemExit(
            "ADMIN_PASSWORD debe tener al menos 12 caracteres y no ser la clave demo"
        )

    with SessionLocal() as db:
        _, created = ensure_admin(
            db,
            settings.admin_email,
            settings.admin_password,
        )
        db.commit()
        print(
            "Administrador creado"
            if created
            else "Administrador existente actualizado"
        )


if __name__ == "__main__":
    main()