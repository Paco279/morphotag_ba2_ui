# morphotag_ba2_ui

Una Interfaz de Usuario para el proceso de morphotag de BatchAlign2.

## Instalación (editable)

```bash
python -m venv .venv && source .venv/bin/activate   # in Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

## CLI

*    ba2-clean <carpeta> → limpia/valida y separa en clean/ y needs_review/.
*    ba2-diagnose <archivo|carpeta> → diagnóstico legible (API batchalign), sin modificar.
*    ba2-alignpatch <carpeta> → leer con pylangacq aplicando post-fix mínimo si hace falta.
*    ba2-build-df <carpeta> → CSVs de tokens e incidencias sin pylangacq.
*    ba2-transcribe <audio> → (fase 2) transcribe audio con faster-whisper.



## Cómo usar (rápido)

```bash
# 1) Instalar en editable
cd ba2kit
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2) Limpiar/validar
ba2-clean /ruta/a/tu/input

# 3) Diagnosticar archivos con problemas
ba2-diagnose /ruta/a/tu/input/needs_review

# 4) (Opcional) Crear CSVs sin pylangacq
ba2-build-df /ruta/a/tu/input/clean --out_csv tokens.csv --issues_csv issues.csv

# 5) (Opcional) Leer con pylangacq aplicando post-fix si hace falta
ba2-alignpatch /ruta/a/tu/input/clean