# Shuttle Codec

**Una GUI moderna, elegante y potente para FFmpeg** — Convierte videos sin escribir un solo comando.

<p align="center">
  <img src="logo.png" alt="Shuttle Codec Logo" width="128"/>
</p>

> Convierte cualquier archivo de video con solo arrastrar y soltar. Soporta lote, aceleracion por hardware NVENC, recorte de video, conversion a GIF y modo experto. Tema oscuro estilo Catppuccin Mocha. Interfaz responsive adaptable a cualquier tamano de pantalla.

---

## Caracteristicas principales

### Faciles de usar
- **Modo Simple/Experto**: Por defecto modo simple (solo formato), toggle para opciones avanzadas
- **Arrastra y suelta**: Soporta multiples archivos a la vez
- **Atajos de teclado**: Ctrl+O (abrir), Ctrl+E (convertir), Ctrl+Q (salir), Delete (quitar)
- **Deteccion automatica**: Al cargar un video analiza codec, resolucion y sugiere la configuracion optima
- **Panel de informacion**: Codecs, resolucion, tamano y duracion visibles siempre al cargar un archivo
- **Responsive**: La interfaz se adapta a cualquier tamano de ventana con scroll automatico

### Potentes
- **Conversion de video**: MP4 (H.264/H.265), MKV, AVI, MOV, WebM, **GIF**
- **Conversion de audio**: MP3, AAC, WAV, FLAC, OGG, M4A, WMA
- **Procesamiento por lotes**: Convierte multiples archivos con la misma configuracion
- **Conversion a GIF**: Genera GIFs optimizados con palette optimizada (palettegen + paletteuse)
- **Recorte de video**: Selecciona inicio y fin para recortar segmentos especificos (duracion en tiempo real)
- **Aceleracion por hardware**: Detecta automaticamente NVENC (NVIDIA), AMF (AMD) o QSV (Intel)
- **Control fino**: CRF, preset de codificacion, resolucion, FPS, codec de audio y mas

### Informativas
- **ETA y velocidad**: Tiempo restante estimado y velocidad durante la conversion
- **Info del archivo**: Codecs, resolucion, bitrate, duracion al cargar
- **Persistencia**: Recuerda tamano/posicion de ventana y ultimas configuraciones
- **Log detallado**: Registro completo de todas las operaciones

---

## Tecnologias

| Capa | Tecnologia |
|------|-----------|
| Lenguaje | Python 3.11 |
| GUI | PyQt5 |
| Motor de video | FFmpeg (embebido) |
| Empaquetado | PyInstaller |
| Tema | Catppuccin Mocha |

---

## Requisitos

- **Para usar el ejecutable**: Windows 10/11 (64-bit)
- **Para desarrollo**: Python 3.8+

## Instalacion (desarrolladores)

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

## Compilar ejecutable (con FFmpeg embebido)

El ejecutable incluye FFmpeg y FFprobe, **sin necesidad de descargarlos aparte** si ya los tienes en `resources/bin/`.

```bash
# 1. Descargar FFmpeg (solo primera vez)
python download_ffmpeg.py

# 2. Compilar
pip install pyinstaller
python build.py
```

El ejecutable estara en `dist/shuttle-codec.exe`.

## Como usar

1. Abre la app o arrastra un archivo
2. Configura formato, resolucion, calidad y demas opciones
3. Opcional: agrega mas archivos al lote, activa recorte o modo GIF
4. Haz clic en **Iniciar conversion**

---

## Licencia

Apache 2.0 — Con atribucion y proteccion de patentes.

---

<p align="center">
  <b>Shuttle Codec</b> — Hecho por <a href="https://github.com/jmarc9901">@jmarc9901</a>
</p>
