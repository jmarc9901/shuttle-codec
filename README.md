# 🚀 Shuttle Codec

**Una GUI moderna, elegante y potente para FFmpeg** — Convierte videos sin escribir un solo comando.

<p align="center">
  <img src="logo.png" alt="Shuttle Codec Logo" width="128"/>
</p>

> Convierte cualquier archivo de video con solo arrastrar y soltar. Soporta lote, aceleración por hardware NVENC, recorte de video y modo experto. Tema oscuro estilo Catppuccin Mocha. 🎨⚡

---

## ✨ Características principales

### 🎯 Fáciles de usar
- **Modo Simple/Experto**: Por defecto modo simple (solo formato), toggle para opciones avanzadas
- **Arrastra y suelta**: Soporta múltiples archivos a la vez
- **Atajos de teclado**: Ctrl+O (abrir), Ctrl+E (convertir), Ctrl+Q (salir), Delete (quitar)
- **Detección automática**: Al cargar un video analiza códec, resolución y sugiere la configuración óptima

### ⚡ Potentes
- **Conversión de video**: MP4 (H.264/H.265), MKV, AVI, MOV, WebM
- **Conversión de audio**: MP3, AAC, WAV, FLAC, OGG, M4A, WMA
- **Procesamiento por lotes**: Convierte múltiples archivos con la misma configuración
- **Recorte de video**: Selecciona inicio y fin para recortar segmentos específicos
- **Aceleración por hardware**: Detecta automáticamente NVENC (NVIDIA), AMF (AMD) o QSV (Intel)
- **Control fino**: CRF, preset de codificación, resolución, FPS, códec de audio y más

### 📊 Informativas
- **ETA y velocidad**: Tiempo restante estimado y velocidad durante la conversión
- **Info del archivo**: Codecs, resolución, bitrate, duración al cargar
- **Persistencia**: Recuerda tamaño/posición de ventana y últimas configuraciones
- **Log detallado**: Registro completo de todas las operaciones

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.11 |
| GUI | PyQt5 |
| Motor de video | FFmpeg (embebido) |
| Empaquetado | PyInstaller |
| Tema | Catppuccin Mocha |

---

## 📦 Requisitos

- **Para usar el ejecutable**: Windows 10/11 (64-bit)
- **Para desarrollo**: Python 3.8+

## 🔧 Instalación (desarrolladores)

```bash
# Clonar repositorio
git clone https://github.com/jmarc9901/shuttle-codec.git
cd shuttle-codec

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python -m src.main
```

## 🏗️ Compilar ejecutable (con FFmpeg embebido)

El ejecutable incluye FFmpeg y FFprobe, **sin necesidad de descargarlos aparte**.

```bash
# 1. Descargar FFmpeg (solo primera vez)
pip install py7zr
python download_ffmpeg.py

# 2. Compilar
pip install pyinstaller
python build.py
```

El ejecutable estará en `dist/shuttle-codec.exe`.

## 🎯 Cómo usar

1. Abre la app o arrastra un archivo
2. Configura formato, resolución, calidad y demás opciones
3. Opcional: agrega más archivos al lote, activa recorte o modo experto
4. Haz clic en **Iniciar conversión**


---

## 📄 Licencia

Apache 2.0 — Con atribución y protección de patentes.

---

<p align="center">
  <b>Shuttle Codec</b> — Hecho por <a href="https://github.com/jmarc9901">@jmarc9901</a>
</p>
