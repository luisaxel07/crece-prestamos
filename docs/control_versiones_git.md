# Git y GitHub: ejecución personal y evidencia

Estos comandos son para que el responsable los ejecute personalmente en **Git Bash**, uno por uno. No se han inicializado repositorios, creado commits ni publicado archivos automáticamente. Los commits registrarán la incorporación por bloques del estado actual del proyecto; no representan un historial de desarrollo en fechas anteriores.

## 1. Ubicación y herramienta

```bash
cd "/c/Users/Precision/Desktop/CRECE PRESTAMOS/CRECE Prestamos"
```

```bash
pwd
```

```bash
git --version
```

Conserva una captura del resultado. Si la carpeta ya tiene un repositorio, revisa primero `git status` y su historial antes de seguir; no lo reemplaces.

## 2. Inicializar y registrar tu identidad

```bash
git init -b main
```

En los dos comandos siguientes sustituye los textos por tu nombre y el correo que quieras asociar a tus commits. No requieren la contraseña de GitHub.

```bash
git config user.name "TU NOMBRE"
```

```bash
git config user.email "TU CORREO DE COMMITS"
```

```bash
git config --get user.name
```

```bash
git config --get user.email
```

## 3. Primer bloque: configuración

```bash
git add .gitignore README.md requirements.txt conexion.example.py
```

```bash
git check-ignore -v conexion.py
```

Debe mostrar que la configuración privada queda excluida. `conexion.example.py` sí debe aparecer entre los archivos preparados. La conexión local existente se conserva.

```bash
git status --short
```

```bash
git diff --cached --stat
```

```bash
git commit -m "Preparar configuración y requisitos de CRECE Prestamos"
```

Captura los archivos preparados y el resultado del commit.

## 4. Segundo bloque: reglas, ORM y MySQL

```bash
git add crece/__init__.py crece/nucleo crece/infraestructura crece/servicios database
```

```bash
git diff --cached --stat
```

```bash
git commit -m "Incorporar reglas financieras, ORM y migraciones MySQL"
```

## 5. Tercer bloque: escritorio

```bash
git add ui services styles assets app.py main.py portal_cliente.py crece/interfaz.py
```

```bash
git diff --cached --stat
```

```bash
git commit -m "Incorporar aplicación PySide6 y gestión administrativa"
```

## 6. Cuarto bloque: web

```bash
git add portal_web
```

```bash
git diff --cached --stat
```

```bash
git commit -m "Incorporar portal web con acceso por roles"
```

## 7. Quinto bloque: pruebas

```bash
git add tests pruebas
```

```bash
git diff --cached --stat
```

```bash
git commit -m "Incorporar pruebas de negocio, interfaces y recuperación"
```

## 8. Sexto bloque: documentación

```bash
git add docs tools GUIA_ACCESO_PREMIUM.md GUIA_INTERFAZ_PREMIUM.md GUIA_PORTAL_CLIENTE.md GUIA_TEMAS.md
```

```bash
git diff --cached --stat
```

```bash
git commit -m "Documentar sesiones académicas y demostración del sistema"
```

```bash
git status
```

```bash
git log --oneline --graph --decorate
```

Conserva una captura del historial y del estado final. No uses `git add .` si aún no has revisado qué archivos quedarían incluidos. Si faltan archivos nuevos, revísalos antes de decidir a qué bloque pertenecen.

## 9. Publicar personalmente en GitHub

Desde tu cuenta crea un repositorio vacío, sin README, licencia ni .gitignore iniciales, y elige la visibilidad que corresponda a la entrega. Copia su URL HTTPS. En el siguiente comando sustituye `URL_HTTPS_COPIADA` por esa URL completa.

```bash
git remote add origin URL_HTTPS_COPIADA
```

```bash
git remote -v
```

```bash
git push -u origin main
```

Completa la autenticación en el navegador si Git la solicita. Captura el resultado del envío, el listado de archivos en GitHub y la página de commits: el envío conserva todos los commits que hiciste localmente, no los fusiona en uno solo.

La carpeta versionada es la aplicación `CRECE Prestamos`. Los PDF de las clases, el antecedente Brainrot Company, archivos temporales y documentos externos a esta carpeta no se añaden automáticamente. El PDF académico del sistema tiene una copia en `docs/` para incorporarlo con la documentación.
