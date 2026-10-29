# Validación

## 2026-10-21 — condiciones renderizadas en el cliente

Base: `5623de4`. Adaptación en `terms.py`; pruebas en `tests/test_terms.py`.

- Windows/Python 3.11: `python -m unittest discover -s tests -v`: **19 aprobadas**.
  Siete pruebas nuevas cubren el formato renderizado, campos ausentes, cliente
  inseguro, plantilla incorrecta/ambigua y precedencia del formulario anterior.
- Lectura autenticada del proveedor: respuesta HTTP 200 sin formularios ni
  inputs; el parser corregido obtiene los once nombres de campos esperados.
  El diagnóstico se detuvo antes de enviar el formulario.
- Tras autorización expresa del titular para aceptar las condiciones v4.0:
  inicio de sesión real **correcto** y consulta de vehículos **uno asociado**.
- Revisión independiente con Sol, razonamiento bajo: **aprobado**, sin bloqueos.
- Home Assistant 2026.10.2: copia previa del archivo, verificación SHA256 y
  comprobación de configuración **valid**. Recuperación tras reinicio **verificada**: integración `loaded`, dieciocho
  entidades disponibles; lecturas de batería y odómetro actualizadas a las
  08:08:20 Europe/Madrid. Sin errores de CUPRA en system_log del nuevo arranque.
  Se restituyó el estado de calefacción previo al reinicio (calor, 22 °C).

No se guardaron cuerpos autenticados ni secretos en las pruebas o el repositorio.
Las fixtures son sintéticas. Las condiciones son legales: la comprobación real
solo se realizó después de obtener autorización explícita del titular.

## 2026-10-29 — formulario de identidad universal

- Windows: `python -m unittest discover -s tests`: 21 pruebas aprobadas.
- Home Assistant 2026.10.4: inicio de sesión real al arrancar, entrada cargada
  y 18 entidades disponibles. Archivo instalado SHA-256 `fdc695d073fb8799e73248bf5f882d38e4e26ca873f4d0e0b57ea929bf669753`.
- Sin comprobar: formulario interactivo de reautenticación y caducidad natural.
