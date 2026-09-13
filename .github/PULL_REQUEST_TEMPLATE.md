<!--
Gracias por tu contribución. Nota: este archivo debe ser Markdown, no un
formulario YAML (GitHub solo interpreta como formulario los de ISSUE_TEMPLATE/).
-->

## Resumen

<!-- Qué hace este PR y por qué es necesario. -->

## Tipo de cambio

- [ ] Corrección de bug
- [ ] Nueva funcionalidad
- [ ] Refactor
- [ ] Documentación
- [ ] Tests / CI
- [ ] Otro:

## Cómo lo he verificado

<!-- Qué pruebas has hecho: automáticas y manuales. -->

## Checklist

- [ ] `python -m pytest tests/ -v` pasa
- [ ] `ruff check .` no reporta nada
- [ ] `mypy src/` (modo strict) no reporta nada
- [ ] He añadido o actualizado los tests que cubren el cambio
- [ ] Si añadí texto de interfaz, está en **ambos** idiomas (`src/i18n.py`)
- [ ] Si añadí un contenedor, actualicé `COPY_SAFE_AUDIO_CODECS`
- [ ] He actualizado la documentación afectada (README, `docs/`, `CHANGELOG.md`)

## Issue relacionado

<!-- Closes #123 -->
