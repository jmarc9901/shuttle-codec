# Shuttle Codec

**Una GUI moderna, elegante y potente para FFmpeg** — Convierte videos sin escribir un solo comando.

<p align="center">
  <img src="logo.png" alt="Shuttle Codec Logo" width="128"/>
</p>

<p align="center">
  <a href="https://github.com/jmarc9901/shuttle-codec/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/jmarc9901/shuttle-codec/ci.yml?branch=main&label=CI" alt="CI">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec">
    <img src="https://img.shields.io/github/stars/jmarc9901/shuttle-codec?style=flat&label=Stars" alt="Stars">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec/releases">
    <img src="https://img.shields.io/github/v/release/jmarc9901/shuttle-codec" alt="Release">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec/blob/main/CONTRIBUTING.md">
    <img src="https://img.shields.io/badge/contributions-welcome-brightgreen" alt="Contributions">
  </a>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a>
</p>

> Convierte cualquier archivo de video, audio o imagen con solo arrastrar y soltar. Soporta lote, aceleracion por hardware NVENC/AMF/QSV (con fallback automatico a CPU), recorte de video, conversion a GIF, conversion de imagenes y extraccion de fotogramas, compresion a tamano objetivo, extraccion de audio y modo experto. Tema oscuro estilo Catppuccin Mocha. Interfaz adaptable a cualquier tamano de pantalla.

---

## Demo

<p align="center">
  <img src="docs/demo.gif" alt="Shuttle Codec demo" width="800"/>
</p>

---

## Caracteristicas principales

### Faciles de usar
- **Modo Simple/Experto**: Por defecto modo simple (solo formato), toggle para opciones avanzadas
- **Arrastra y suelta**: Soporta multiples archivos a la vez
- **Atajos de teclado**: Ctrl+O (abrir), Ctrl+E (convertir), Ctrl+Q (salir), Delete (quitar)
- **Deteccion automatica**: Al cargar un video analiza codec, resolucion y sugiere la configuracion optima
- **Panel de informacion**: Codecs, resolucion, tamano y duracion visibles siempre al cargar un archivo
- **Responsive**: La interfaz se adapta a cualquier tamano de ventana con scroll automatico
- **🌐 Internacionalizacion**: Interfaz en Español e Ingles, seleccionable desde la cabecera

### Potentes
- **Conversion de video**: MP4 (H.264/H.265), MKV, AVI, MOV, WebM, **GIF**
- **Conversion de audio**: MP3, AAC, WAV, FLAC, OGG, M4A, WMA (archivos solo de audio)
- **Extraer audio**: saca la pista de audio de cualquier video (MP3, AAC, FLAC, …)
- **Conversion de imagenes**: PNG, JPG, WebP, BMP, TIFF con calidad y reescalado Lanczos
- **Exportar fotograma**: guarda un fotograma del video como imagen en cualquier instante
- **Tamano objetivo**: «comprime esto a 25 MB» — el bitrate se calcula solo
- **Procesamiento por lotes**: Convierte multiples archivos con la misma configuracion; la cola sobrevive al reinicio
- **Conversion a GIF**: Genera GIFs optimizados con palette optimizada (palettegen + paletteuse)
- **Recorte de video**: Selecciona inicio y fin para recortar segmentos especificos (duracion en tiempo real)
- **Aceleracion por hardware**: Detecta automaticamente NVENC (NVIDIA), AMF (AMD) o QSV (Intel), y **reintenta en la CPU automaticamente** si el encoder de la GPU falla en ejecucion
- **Apagar al terminar**: lotes desatendidos, con cuenta atras de 60 s cancelable
- **Control fino**: CRF, preset de codificacion, resolucion, FPS, codec de audio y mas

### Informativas
- **ETA y velocidad**: Tiempo restante estimado y velocidad durante la conversion
- **Info del archivo**: Codecs, resolucion, bitrate, duracion al cargar
- **Estimacion de tamano**: pronostico `≈ MB` que sigue tus ajustes
- **Persistencia**: Recuerda tamano/posicion de ventana, idioma, ultimas configuraciones y la cola de lote
- **Log detallado**: Registro completo de todas las operaciones, incluido el comando exacto de FFmpeg
- **Reporte de errores en un clic**: el boton 🐞 abre una incidencia en GitHub ya rellena con el diagnostico

---

## Tecnologias

| Capa | Tecnologia |
|------|-----------|
| Lenguaje | Python 3.10+ |
| GUI | PyQt5 |
| Motor de video | FFmpeg (embebido) |
| Empaquetado | PyInstaller |
| Tema | Catppuccin Mocha |
| Testing | pytest + unittest.mock |

---

## Inicio rapido

### Opcion 1: Descargar (Recomendado)
1. Ve a la [ultima version](https://github.com/jmarc9901/shuttle-codec/releases/latest)
2. Descarga el instalador (`shuttle-codec-<version>-setup.exe`) o el
   `shuttle-codec.exe` portable
3. Ejecutalo — FFmpeg ya viene incluido

Cada release publica `SHA256SUMS.txt` para que puedas verificar la descarga.

### Opcion 2: Desde codigo fuente

```bash
# Clonar repositorio
git clone https://github.com/jmarc9901/shuttle-codec.git
cd shuttle-codec

# Instalar dependencias
pip install -r requirements.txt

# Descargar FFmpeg (solo primera vez)
python download_ffmpeg.py

# Ejecutar
python -m src.main
```

### Compilar ejecutable

```bash
python download_ffmpeg.py
pip install -e ".[build]"   # pyinstaller + pillow
python build.py
```

El ejecutable estara en `dist/shuttle-codec.exe`.

Tambien puedes generar un instalador de Windows con
[Inno Setup](https://jrsoftware.org/isinfo.php):

```bash
iscc installer/shuttle-codec.iss /DMyAppVersion=1.3.0
```

---

## Documentacion

| Documento | Contenido |
|-----------|-----------|
| [Guia de usuario](docs/USER_GUIDE.es.md) ([en](docs/USER_GUIDE.md)) | Todas las funciones, paso a paso |
| [Problemas y FAQ](docs/TROUBLESHOOTING.es.md) ([en](docs/TROUBLESHOOTING.md)) | Problemas habituales, formatos, privacidad |
| [Releasing](docs/RELEASING.md) | Proceso de release, firma de codigo, pin de FFmpeg |
| [CHANGELOG](CHANGELOG.md) | Historial de versiones |

---

## Novedades de la v1.3.0

### ✨ Añadido
- **Conversion de imagenes**: salida PNG, JPG, WebP, BMP y TIFF con deslizador de
  calidad y reescalado Lanczos — el filtro de archivos ya no promete imagenes que
  la aplicacion no podia manejar.
- **Exportar fotograma**: guarda un fotograma del video como imagen en cualquier
  instante (busca antes de `-i`, asi que es instantaneo incluso en archivos largos).
- **Tamano objetivo**: pide un tamano en MB y el bitrate se calcula solo (control
  de tasa en una pasada); la estimacion de tamano se actualiza en vivo.
- **Extraer solo el audio**: conserva unicamente la pista de audio del video, en
  cualquier formato soportado.
- **Fallback automatico a CPU**: si el encoder de la GPU falla en ejecucion
  (driver antiguo, GPU ocupada, limite de sesiones) el trabajo se reintenta en
  software en lugar de fallar.
- **Cola de lote persistente** y **apagado al terminar**, con cuenta atras de 60
  segundos cancelable.
- **Reporte de errores en un clic**: incidencia de GitHub rellenada con version,
  sistema, versiones de Python/Qt/FFmpeg y el registro (nunca se envia solo).
- **Estimacion del tamano de salida** (`📏 ≈ MB`) en el panel de informacion.

### 🐛 Corregido
- **Diaologo ilegible al terminar**: el mensaje tras una conversion mostraba
  texto claro sobre fondo claro. Los dialogos, tooltips y menus siguen ahora el
  tema oscuro tanto por stylesheet como por la paleta de la aplicacion.
- **La calidad AMF se ignoraba**: `h264_amf`/`hevc_amf` aplican ya el CRF via
  `-rc cqp -qp_i/-qp_p` en lugar de solo `-quality balanced`.
- El comando de fallback se reescribe en su sitio, sin dejar opciones despues de
  la ruta de salida (donde FFmpeg avisa y las ignora).

### 🚀 Distribucion y calidad
- **Instalador de Windows** (Inno Setup, `installer/shuttle-codec.iss`), **zip de
  macOS** y **AppImage de Linux** (best effort) en el workflow de release.
- **Checksums SHA-256** publicados en cada release, con ganchos opcionales de
  firma y notarizacion (ver [RELEASING.md](docs/RELEASING.md)).
- **Pin de FFmpeg**: `FFMPEG_BUILD_TAG` + `FFMPEG_ARCHIVE_SHA256` hacen los
  binarios reproducibles y verificables; el script se niega a extraer un archivo
  que no coincide.
- **Version con una sola fuente** (`src/__init__.py`), escalado HiDPI y un job de
  CI que compila el ejecutable en Windows.
- **232 tests unitarios** con minimo de cobertura exigido (80%, hoy ~82%);
  `ruff` limpio en todo el arbol y `mypy` limpio en `src/`.

### 📚 Documentacion
- Guia de usuario, problemas/FAQ y documentacion de release en ingles y español.

> Versiones anteriores: consulta [CHANGELOG.md](CHANGELOG.md).

---

## Desarrollo

```bash
pip install -e ".[dev]"

python -m pytest tests/ -v                          # 232 tests unitarios
python -m pytest tests/ --cov=src --cov-report=term # cobertura (minimo: 80%)
ruff check .                                        # lint
mypy src/                                           # chequeo de tipos
```

---

## Estructura del proyecto

```
shuttle-codec/
├── src/
│   ├── __init__.py
│   ├── main.py               # Punto de entrada
│   ├── app.py                # Ventana principal (PyQt5) + orquestacion
│   ├── workers.py            # Worker QThread + gestor de lote
│   ├── ffmpeg_handler.py     # Construccion/ejecucion de comandos FFmpeg
│   ├── ffmpeg_downloader.py  # Busqueda de binarios (embebidos vs sistema)
│   ├── presets.py            # Presets por caso de uso + mapa de resoluciones
│   ├── theme.py              # Paleta y stylesheet Catppuccin Mocha
│   ├── utils.py              # Icono y helpers de tiempo/tamano
│   ├── diagnostics.py        # Texto de diagnostico y URL de incidencia
│   └── i18n.py               # Traducciones ES/EN
├── tests/
│   ├── test_app_smoke.py        # UI headless (se omite sin Qt)
│   ├── test_ffmpeg_handler.py   # comandos, formatos, hardware, recorte, audio, imagenes
│   ├── test_ffmpeg_downloader.py
│   ├── test_download_ffmpeg.py  # seguridad e integridad de la extraccion
│   ├── test_diagnostics.py      # composicion del informe
│   ├── test_workers.py          # gestor de lote y fallback a CPU
│   ├── test_presets.py
│   ├── test_theme.py
│   ├── test_utils.py
│   └── test_i18n.py
├── installer/               # Script de Inno Setup (instalador Windows)
├── docs/                    # Guia de usuario, FAQ, notas de release, demo.gif
├── resources/bin/           # Binarios FFmpeg embebidos
├── download_ffmpeg.py       # Descarga FFmpeg desde GitHub
├── build.py                 # Build con PyInstaller
├── pyproject.toml
└── requirements.txt
```

---

## Licencia

Apache 2.0 — Con atribucion y proteccion de patentes.

---

<p align="center">
  <b>Shuttle Codec</b> — Hecho por <a href="https://github.com/jmarc9901">@jmarc9901</a>
</p>
