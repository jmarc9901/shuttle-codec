name: Pull Request
description: Enviar cambios al proyecto
title: "[FEATURE/FIX] Título descriptivo"
body:
  - type: markdown
    attributes:
      value: |
        Gracias por tu contribución. Por favor completa esta información.

  - type: textarea
    id: summary
    attributes:
      label: Resumen
      description: Explica qué hace este PR y por qué es necesario.
    validations:
      required: true

  - type: dropdown
    id: type
    attributes:
      label: Tipo de cambio
      multiple: false
      options:
        - Bug fix
        - Nueva feature
        - Refactor
        - Documentación
        - Tests
        - Otro

  - type: textarea
    id: testing
    attributes:
      label: Testing
      description: ¿Cómo verificaste que los cambios funcionan?
      placeholder: |
        - Ejecuté `python -m pytest tests/ -v`
        - Probé manualmente la conversión de MP4 a GIF
    validations:
      required: true

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist
      options:
        - label: Los tests pasan (`python -m pytest tests/ -v`)
          required: true
        - label: El código tiene type hints
          required: true
        - label: No hay errores de sintaxis
          required: true
