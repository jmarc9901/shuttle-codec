# Solución de problemas y preguntas frecuentes

🌐 **English:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

Antes de nada: el panel **Registro** de la parte inferior contiene el comando
exacto de FFmpeg y su salida. Cuando informes de un problema, pulsa
**🐞 Reportar** para adjuntar esa información automáticamente.

---

## La aplicación no arranca (Windows)

- **«Windows protegió tu PC»** — es SmartScreen en compilaciones sin firmar.
  Pulsa *Más información* → *Ejecutar de todas formas*, o usa el instalador
  firmado del proyecto.
- **No pasa nada al hacer doble clic** — ejecútalo desde una terminal
  (`.\shuttle-codec.exe`) para ver el error. A veces el antivirus pone en
  cuarentena los ejecutables recién creados con PyInstaller; permite el archivo
  e inténtalo de nuevo.
- **La ventana se ve diminuta o borrosa** — la aplicación activa el escalado
  HiDPI de Qt. En configuraciones con varios monitores y factores de escala
  distintos, cierra la sesión de Windows y vuelve a entrar.

## macOS: «shuttle-codec está dañado y no se puede abrir»

Gatekeeper bloquea binarios sin firmar o en cuarentena. Compílalo desde el
código o quita el atributo de cuarentena:

```bash
xattr -dr com.apple.quarantine ./shuttle-codec
```

## Linux: el AppImage no arranca

```bash
chmod +x shuttle-codec-x86_64.AppImage
./shuttle-codec-x86_64.AppImage
```

Si no hay FUSE disponible (habitual en contenedores), ejecútalo con
`--appimage-extract-and-run`.

Si el release que has descargado no trae AppImage (se compila best-effort), usa
el binario `shuttle-codec` del mismo release: dale permisos con `chmod +x` y
ejecútalo, es la misma aplicación.

## «FFmpeg: ✗» en la cabecera

Shuttle Codec busca los binarios en este orden:

1. `resources/bin/` junto a la aplicación (las compilaciones incluyen FFmpeg ahí).
2. Tu `PATH` del sistema.

Si no los encuentra, instala FFmpeg (`winget install Gyan.FFmpeg`,
`brew install ffmpeg`, `sudo apt install ffmpeg`) o ejecuta
`python download_ffmpeg.py` en una copia del código fuente.

## La aceleración por hardware falla o está en gris

- La casilla solo aparece cuando FFmpeg informa de un codificador usable
  (NVENC/AMF/QSV); la cabecera indica cuál se detectó.
- Si la codificación falla igualmente, Shuttle Codec **reintenta en la CPU
  automáticamente** y deja un aviso en el registro. Es la causa más común de
  «mis conversiones siempre fallaban» y ya está resuelta.
- Para forzar la CPU, simplemente deja la casilla desmarcada.

## El tamaño del archivo no coincide con la estimación

La estimación `📏 ≈` es una aproximación calibrada con H.264 CRF 23 a 30 fps. La
complejidad manda: una pantalla estática ocupa mucho menos que una escena con
movimiento. Si necesitas un límite duro, usa **Tamaño objetivo**: ese modo
calcula el bitrate a partir del tamaño que pides.

## El tamaño objetivo no cambia nada

Ese modo necesita la duración para derivar el bitrate. Si FFprobe no puede leerla
(contenedores raros, imágenes, cabeceras corruptas), la conversión cae a CRF y el
registro lo indica. Recodificar el archivo primero suele arreglar los metadatos:
`ffmpeg -i roto.mkv -c copy arreglado.mp4`.

## «Hay una conversión en curso. ¿Cancelar y salir?» al cerrar

Shuttle Codec pregunta antes de matar un trabajo en marcha. Con *Sí* se cancela
el proceso de FFmpeg; el archivo parcial se borra antes de un reintento, pero una
conversión cancelada deja lo que FFmpeg hubiera escrito: bórralo si no lo quieres.

## ¿Dónde se guardan mis ajustes? ¿Cómo los reinicio?

En el almacén de ajustes de Qt:

- Windows: clave del registro `HKCU\Software\ShuttleCodec`
- macOS: `~/Library/Preferences/com.ShuttleCodec.ShuttleCodec.plist`
- Linux: `~/.config/ShuttleCodec.conf`

Borra esa clave/archivo para tener un estado limpio como en el primer arranque.

## La cola de lote aparece vacía al reiniciar

La cola se restaura de la sesión anterior, pero los archivos que ya no existen
(renombrados, movidos, disco externo desconectado) se ignoran en silencio. La
cola es una simple lista de rutas: si prefieres automatizarlo, puedes convertir
esos archivos por línea de comandos con FFmpeg.

## ¿Se puede usar desde la línea de comandos?

Shuttle Codec es una interfaz gráfica, pero el comando de FFmpeg que genera
aparece en el registro, así que puedes copiarlo a un script. Instala el paquete
(`pip install -e .`) y ejecuta `shuttle-codec` para abrirlo desde cualquier sitio.

## ¿Sube mis archivos o recoge datos?

No. La aplicación no hace ninguna petición de red: el único acceso a la red
ocurre al compilar, al descargar FFmpeg. La versión, el sistema y el registro
solo se envían si pulsas **Reportar** y envías tú mismo la incidencia en GitHub.

## Formatos soportados

- **Vídeo de salida**: MP4 (H.264, H.265), MKV, AVI, MOV, WebM (VP9), GIF
- **Audio de salida**: MP3, AAC, WAV, FLAC, OGG (Vorbis), M4A, WMA
- **Imagen de salida**: PNG, JPG, WebP, BMP, TIFF (además de exportar un
  fotograma de un vídeo)
- **Entrada**: cualquiera que FFmpeg pueda decodificar (cientos de contenedores y
  códecs)

## «Archivo no válido o no soportado» con un archivo correcto

Shuttle Codec acepta archivos de hasta **10 GB** que FFmpeg pueda decodificar.
Los archivos vacíos, los que no tienen una extensión multimedia y los que
superan ese límite se rechazan antes de empezar la conversión. Para archivos más
grandes, copia el comando del panel Registro y ejecútalo con FFmpeg directamente.

## La conversión va muy lenta

- Activa la aceleración por hardware si la casilla está disponible.
- Usa un preset más rápido (`ultrafast`/`veryfast`) en lugar de `slow`.
- Evita H.265 en archivos grandes salvo que necesites el tamaño pequeño: en CPU
  es bastante más lento que H.264.
- VP9 en WebM es solo CPU y lento por diseño.
