# Contributing to Shuttle Codec

¡Gracias por tu interés en contribuir! 🙌

## Cómo contribuir

### Reportar bugs

1. Verifica que el bug no haya sido reportado ya en [Issues](https://github.com/jmarc9901/shuttle-codec/issues)
2. Usa la plantilla de **Bug Report** al crear el issue
3. Incluye:
   - Pasos para reproducir
   - Comportamiento esperado vs actual
   - Logs de error (de la ventana de registro de la app)
   - Sistema operativo y versión de Python

### Sugerir features

1. Revisa los issues existentes para ver si ya se sugirió
2. Usa la plantilla de **Feature Request**
3. Describe el problema que resuelve y cómo debería funcionar

### Pull Requests

1. **Fork** el repositorio
2. Crea una rama desde `main`: `git checkout -b feature/mi-feature`
3. Haz commits con mensajes claros (en español o inglés)
4. Ejecuta los tests: `python -m pytest tests/ -v`
5. Asegúrate de que el código pase el lint: `ruff check src/`
6. Haz push y abre un Pull Request

#### Estándares de código

- **Python 3.8+** compatible
- **Type hints** en todas las funciones y métodos
- Nombres de variables en inglés (snake_case)
- Comentarios y docstrings en español (idioma del proyecto)
- Sigue el estilo existente del código

#### Antes de hacer commit

```bash
# Verificar que los tests pasan
python -m pytest tests/ -v

# Verificar sintaxis
python -c "import py_compile; py_compile.compile('src/app.py', doraise=True)"
```

## Entorno de desarrollo

```bash
git clone https://github.com/jmarc9901/shuttle-codec.git
cd shuttle-codec
pip install -r requirements.txt
pip install pytest    # Para tests
python download_ffmpeg.py   # Descargar FFmpeg (primera vez)
python -m src.main          # Ejecutar
```

## Licencia

Al contribuir, aceptas que tu código será licenciado bajo [Apache 2.0](LICENSE).
