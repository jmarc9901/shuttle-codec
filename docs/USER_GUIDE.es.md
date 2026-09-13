# Shuttle Codec — Guía de usuario

🌐 **English:** [USER_GUIDE.md](USER_GUIDE.md)

Shuttle Codec convierte vídeo, audio e imágenes con FFmpeg sin escribir ni un
comando. FFmpeg va incluido dentro de la aplicación, así que no hay nada más que
instalar.

---

## 1. Instalación

| Plataforma | Cómo |
|-----------|------|
| Windows | Descarga `shuttle-codec-<versión>-setup.exe` desde la [página de releases](https://github.com/jmarc9901/shuttle-codec/releases) y ejecútalo, o usa el `shuttle-codec.exe` portable |
| macOS | Descarga `shuttle-codec-macos.zip`, descomprímelo y mueve el binario donde quieras |
| Linux | Descarga `shuttle-codec-x86_64.AppImage`, dale permisos (`chmod +x`) y ejecútalo |

> La primera vez, una compilación sin firmar puede ser bloqueada por SmartScreen
> («Windows protegió tu PC» → *Más información* → *Ejecutar de todas formas*) o
> por Gatekeeper. Ese aviso desaparece cuando la release está firmada; mira
> [RELEASING.md](RELEASING.md).

## 2. La interfaz

```
┌───────────────────────────────────────────────────────────────────────┐
│ Shuttle Codec · autor             🐞 Reportar  [idioma]   FFmpeg: ✓  │  cabecera
├───────────────────────────────────────────────────────────────────────┤
│ [ ruta del archivo ................... ]  📁 Examinar  ✕              │  barra de archivo
│ 📄 clip.mp4   📦 42.1 MB   🎬 H264 1920x1080   🎵 AAC   ⏱ 01:23  📏 ≈ 32 MB │  panel de info
├───────────────────────────────────────────────────────────────────────┤
│ ⚙ Mostrar opciones avanzadas                                          │  modo
│ ⚡ Conversión rápida → [ YouTube (1080p H.264) ▾ ]                    │  presets (modo simple)
├───────────────────────────────────────────────────────────────────────┤
│ 🎬 Video            │  📦 Lista de lote                             │
│ 🎵 Audio            │  ...                                          │
│ 🖼 Imagen           │                                               │  modo experto
│ ✂ Recorte           │                                               │
├───────────────────────────────────────────────────────────────────────┤
│ Progreso: ⏱ Tiempo restante 00:12  ⚡ 3.4x                             │
│ ▶ Iniciar conversión        ✕ Cancelar                                │
├───────────────────────────────────────────────────────────────────────┤
│ Registro                                                              │
└───────────────────────────────────────────────────────────────────────┘
```

### Modo simple (por defecto)

Elige un **preset** y pulsa **Iniciar conversión**. Los presets están ajustados
por destino: YouTube 1080p/4K, WhatsApp, Telegram, Discord, GIF para Twitter,
máxima calidad y tamaño pequeño.

### Modo experto

Pulsa **⚙ Mostrar opciones avanzadas** para tener control total:

- **🎬 Video** — formato de salida (MP4 H.264/H.265, MKV, AVI, MOV, WebM VP9,
  GIF), preset del codificador, calidad (CRF), resolución, FPS, conservar el
  audio original, aceleración por hardware, **tamaño objetivo** y **extraer
  solo el audio**.
- **🎵 Audio** — archivos solo-audio (MP3, AAC, WAV, FLAC, OGG, M4A, WMA) y el
  formato que usa *Extraer solo el audio*.
- **🖼 Imagen** — formato de salida (PNG, JPG, WebP, BMP, TIFF), calidad,
  resolución y **exportar un fotograma** de un vídeo.
- **✂ Recorte** — corta un fragmento por tiempo de inicio y fin.
- **📦 Lista de lote** — encola varios archivos y conviértelos uno tras otro.

## 3. Flujos habituales

### Arrastrar y soltar

Suelta uno o varios archivos en cualquier parte de la ventana. Un archivo se
carga para editarlo; varios se añaden automáticamente a la lista de lote.

### Comprimir a un tamaño máximo (p. ej. los 25 MB de Discord)

1. Abre el archivo y cambia a modo experto.
2. Marca **Tamaño objetivo** y escribe `25` MB.
3. Mira la estimación del panel de información (mostrará `≈ 25 MB`).
4. Convierte.

El deslizador de CRF se desactiva en este modo: Shuttle Codec calcula el bitrate
necesario para acercarse a ese tamaño. Si el archivo no tiene duración legible,
vuelve a calidad constante automáticamente.

### Exportar un fotograma (miniatura / captura)

1. Carga el vídeo y cambia a modo experto.
2. En **🖼 Imagen**, marca **Exportar un fotograma** y elige el instante.
3. Elige PNG (sin pérdida) o JPG/WebP (más pequeños) y convierte.

### Convertir imágenes

Al cargar un `.png`, `.jpg`, `.webp`, `.bmp` o `.tiff`, la ventana pasa a modo
imagen: elige formato de salida, calidad y resolución (reescalado Lanczos) y
convierte. La conversión por lotes de imágenes funciona igual.

### Extraer el audio de un vídeo

Marca **Extraer solo el audio** en el grupo Video, elige MP3/AAC/FLAC/… en el
grupo Audio y convierte. La pista de vídeo se descarta (`-vn`).

### Convertir una carpeta entera

Añade archivos a la **Lista de lote** con ➕, quita los que no quieras con ➖ (o
la tecla `Supr`), y pulsa **Iniciar conversión**. Todos los elementos usan los
ajustes actuales, y la cola se recuerda para la próxima sesión (los archivos que
ya no existen se ignoran).

Marca **Apagar el equipo al terminar** para apagar el PC al acabar un lote
largo. Se muestra una cuenta atrás de 60 segundos que puedes cancelar.

## 4. Aceleración por hardware

Si hay NVENC (NVIDIA), AMF (AMD) o QSV (Intel) disponible, aparece la casilla en
el grupo Video. Actívala para codificar mucho más rápido.

**Si el codificador de la GPU falla por lo que sea** (driver antiguo, GPU
ocupada, demasiadas sesiones), Shuttle Codec reintenta el mismo trabajo en la CPU
en lugar de fallar, y lo indica en el registro. Nunca pierdes una conversión por
culpa de un driver.

## 5. Saber qué vas a obtener

El panel de información muestra siempre la entrada (códec, resolución, tamaño,
duración) y una estimación del tamaño de salida (`📏 ≈ 32 MB`). La estimación es
una aproximación calibrada con H.264 CRF 23; muestra `—` cuando no se puede
calcular (GIF, duración desconocida, bitrate de audio «auto»).

Durante la conversión tienes barra de progreso, tiempo restante y velocidad de
codificación. El panel **Registro** guarda todo, incluido el comando exacto de
FFmpeg que se ejecutó.

## 6. Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+O` | Abrir un archivo |
| `Ctrl+E` | Iniciar la conversión |
| `Ctrl+Q` | Salir |
| `Supr` | Quitar los elementos seleccionados del lote |

## 7. Idioma y ajustes

Usa el selector de idioma de la cabecera para cambiar entre **Español** e
**English**; el cambio es inmediato y se recuerda.

Shuttle Codec recuerda el tamaño y la posición de la ventana, el modo, los
últimos ajustes y la cola de lote. Esa información vive en el almacén de ajustes
de Qt de la aplicación (`HKCU\Software\ShuttleCodec` en Windows y el archivo de
configuración de Qt para `ShuttleCodec` en macOS/Linux).

## 8. Reportar un problema

Pulsa **🐞 Reportar** en la cabecera: se abre GitHub con una incidencia nueva ya
rellena con tu versión, sistema operativo, versiones de Python/Qt/FFmpeg y las
últimas líneas del registro. Describe lo que ha pasado y envíala. Si el navegador
no se puede abrir, ese mismo texto se copia al portapapeles.

## 9. Solución de problemas

Consulta [TROUBLESHOOTING.es.md](TROUBLESHOOTING.es.md).
