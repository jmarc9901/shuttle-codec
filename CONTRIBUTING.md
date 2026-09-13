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
5. Asegúrate de que el código pase lint y tipado: `ruff check .` y `mypy src/`
6. Haz push y abre un Pull Request

#### Estándares de código

- **Python 3.10+** compatible
- **Type hints** en todas las funciones y métodos: `mypy` corre en modo `strict`
- Nombres de variables en inglés (snake_case)
- Comentarios y docstrings en inglés; textos de UI en `src/i18n.py` (ES y EN)
- Sigue el estilo existente del código

Antes de tocar nada, lee [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): explica el
reparto de módulos, el modelo de hilos y los invariantes que no conviene romper.

#### Antes de hacer commit

```bash
# Verificar que los tests pasan (los de FFmpeg real se omiten si no hay binario)
python -m pytest tests/ -v

# Lint, tipado estricto y cobertura
ruff check .
mypy src/
python -m pytest tests/ -q --cov=src --cov-report=term   # minimo 80%
```

O instala los hooks y que se ejecuten solos:

```bash
pip install pre-commit && pre-commit install
```

#### Tests obligatorios para un cambio

- Cualquier cambio en la construccion de comandos necesita su test en
  `tests/test_ffmpeg_handler.py`.
- Si anades un contenedor, anade su entrada en `COPY_SAFE_AUDIO_CODECS`: hay un
test de consistencia que lo comprueba.
- Si anades texto de UI, anade la clave en **los dos** idiomas: la paridad se
  verifica en `tests/test_project_consistency.py`.

## Entorno de desarrollo

```bash
git clone https://github.com/jmarc9901/shuttle-codec.git
cd shuttle-codec
pip install -e ".[dev]"     # PyQt5 + pytest + ruff + mypy
python download_ffmpeg.py   # Descargar FFmpeg (primera vez)
python -m src.main          # Ejecutar
```

## Licencia

Al contribuir, aceptas que tu código será licenciado bajo [Apache 2.0](LICENSE).
