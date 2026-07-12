# Migraciones

Alembic está activo desde la vertical V2. La primera migración (`create conversations and messages`)
crea las tablas `conversations` y `messages`.

`env.py` resuelve la URL de SQLite a partir de `SiriusPaths.data_dir` (directorio local de datos del
usuario en Windows); no depende de una ruta relativa ni de `alembic.ini`, salvo que una llamada explícita
(por ejemplo, en pruebas) fije `sqlalchemy.url`.

Para aplicar las migraciones sobre la base real del usuario:

```powershell
uv run alembic upgrade head
```
