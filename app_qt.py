# app_qt.py — GUI nativa (PySide6) para ba2kit
import os, sys, traceback
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog, QComboBox, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt

from ba2kit.clean import process_dir_to_folders, pretty_summarize_reports
from ba2kit.diagnose import diagnose_with_api_pretty
from ba2kit.parser_light import build_df_from_dir_without_pylangacq

class CleanTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        # Carpeta
        row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        btn_browse = QPushButton("Examinar…")
        btn_browse.clicked.connect(self._pick_dir)
        row.addWidget(QLabel("Carpeta con .cha:"))
        row.addWidget(self.dir_edit)
        row.addWidget(btn_browse)
        lay.addLayout(row)

        # Opciones
        row2 = QHBoxLayout()
        self.missing = QComboBox(); self.missing.addItems(["prefix_com","drop","report"])
        self.empty = QComboBox(); self.empty.addItems(["drop","keep"])
        self.rename = QCheckBox("Renombrar archivos arreglados"); self.rename.setChecked(True)
        row2.addWidget(QLabel("Líneas sin cabecera:")); row2.addWidget(self.missing)
        row2.addWidget(QLabel("Cabeceras vacías:")); row2.addWidget(self.empty)
        row2.addWidget(self.rename)
        lay.addLayout(row2)

        # Ejecutar
        self.btn_run = QPushButton("Procesar carpeta")
        self.btn_run.clicked.connect(self.run)
        lay.addWidget(self.btn_run)

        # Log
        self.out = QTextEdit(); self.out.setReadOnly(True)
        lay.addWidget(self.out)

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Selecciona carpeta con .cha")
        if d: self.dir_edit.setText(d)

    def log(self, txt): self.out.append(txt)

    def run(self):
        folder = self.dir_edit.text().strip()
        if not folder:
            self.log("❌ Indica una carpeta.")
            return
        try:
            reports, clean_dir, review_dir = process_dir_to_folders(
                folder,
                rename_on_change=self.rename.isChecked(),
                backup=True,
                missing_hdr_policy=self.missing.currentText(),
                empty_hdr_policy=self.empty.currentText(),
            )
            self.log(f"✅ Limpios/arreglados → {clean_dir}")
            self.log(f"🧪 Necesitan revisión → {review_dir}")
            self.log("\nResumen de cambios:\n")
            self.out.append(f"<pre>{pretty_summarize_reports(reports)}</pre>")
        except Exception as e:
            self.log("❌ Error:\n" + traceback.format_exc())

class DiagnoseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        btn_browse = QPushButton("Examinar…")
        btn_browse.clicked.connect(self._pick_path)
        row.addWidget(QLabel("Archivo .cha o carpeta:"))
        row.addWidget(self.path_edit)
        row.addWidget(btn_browse)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.before = QSpinBox(); self.before.setRange(0, 20); self.before.setValue(3)
        self.after  = QSpinBox(); self.after.setRange(0, 20);  self.after.setValue(3)
        row2.addWidget(QLabel("Contexto antes:")); row2.addWidget(self.before)
        row2.addWidget(QLabel("después:")); row2.addWidget(self.after)
        lay.addLayout(row2)

        self.btn = QPushButton("Diagnosticar")
        self.btn.clicked.connect(self.run)
        lay.addWidget(self.btn)

        self.out = QTextEdit(); self.out.setReadOnly(True)
        lay.addWidget(self.out)

    def _pick_path(self):
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setNameFilter("CHAT (*.cha);;Todos (*.*)")
        if dlg.exec():
            files = dlg.selectedFiles()
            if files: self.path_edit.setText(files[0])

    def log(self, txt): self.out.append(txt)

    def run(self):
        p = Path(self.path_edit.text().strip())
        if not p.exists():
            d = QFileDialog.getExistingDirectory(self, "Selecciona carpeta con .cha")
            if not d: return
            p = Path(d)
            self.path_edit.setText(str(p))
        files = [p] if p.is_file() else sorted(p.rglob("*.cha"))
        if not files:
            self.log("⚠️ No se encontraron .cha.")
            return
        for f in files:
            d = diagnose_with_api_pretty(str(f), before=self.before.value(), after=self.after.value())
            self.out.append(f"<b>{f.name}</b>")
            if d.get("ok"):
                self.log("✅ Sin errores al parsear (API).")
                continue
            self.log(f"❌ {d.get('error_type','Error')}: {d.get('message','')}")
            meta = []
            if d.get("cha_line") is not None: meta.append(f"Línea estimada: {d['cha_line']}")
            if d.get("py_line")  is not None: meta.append(f"(traceback) última 'line N': {d['py_line']}")
            if meta: self.log(" · " + " · ".join(meta))
            if d.get("utterance"): self.out.append(f"<pre>«{d['utterance']}»</pre>")
            if d.get("context_block"): self.out.append("<pre>" + "\n".join(d["context_block"]) + "</pre>")
            if d.get("hints"): self.out.append("Sugerencias:\n- " + "\n- ".join(d["hints"]))

class CsvTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        btn_browse = QPushButton("Examinar…")
        btn_browse.clicked.connect(self._pick_dir)
        row.addWidget(QLabel("Carpeta con .cha:"))
        row.addWidget(self.dir_edit)
        row.addWidget(btn_browse)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.recursive = QCheckBox("Recursivo"); self.recursive.setChecked(False)
        self.out_tokens = QLineEdit("tokens.csv")
        self.out_issues = QLineEdit("issues.csv")
        row2.addWidget(self.recursive)
        row2.addWidget(QLabel("CSV tokens:")); row2.addWidget(self.out_tokens)
        row2.addWidget(QLabel("CSV issues:")); row2.addWidget(self.out_issues)
        lay.addLayout(row2)

        self.btn = QPushButton("Generar CSVs")
        self.btn.clicked.connect(self.run)
        lay.addWidget(self.btn)

        self.out = QTextEdit(); self.out.setReadOnly(True)
        lay.addWidget(self.out)

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Selecciona carpeta con .cha")
        if d: self.dir_edit.setText(d)

    def log(self, txt): self.out.append(txt)

    def run(self):
        from ba2kit.parser_light import build_df_from_dir_without_pylangacq
        folder = self.dir_edit.text().strip()
        if not folder:
            self.log("❌ Indica carpeta.")
            return
        try:
            df, issues = build_df_from_dir_without_pylangacq(Path(folder), recursive=self.recursive.isChecked())
            df.to_csv(self.out_tokens.text().strip(), index=False, encoding="utf-8")
            issues.to_csv(self.out_issues.text().strip(), index=False, encoding="utf-8")
            self.log(f"✅ Tokens: {df.shape} → {self.out_tokens.text().strip()}")
            self.log(f"✅ Issues: {issues.shape} → {self.out_issues.text().strip()}")
        except Exception:
            self.log("❌ Error:\n" + traceback.format_exc())

class TranscribeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        self.audio_edit = QLineEdit()
        btn_browse = QPushButton("Examinar…")
        btn_browse.clicked.connect(self._pick_audio)
        row.addWidget(QLabel("Audio:"))
        row.addWidget(self.audio_edit)
        row.addWidget(btn_browse)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.lang = QLineEdit("es")
        self.model_size = QComboBox(); self.model_size.addItems(["tiny","base","small","medium","large-v3"])
        row2.addWidget(QLabel("Idioma:")); row2.addWidget(self.lang)
        row2.addWidget(QLabel("Modelo:")); row2.addWidget(self.model_size)
        lay.addLayout(row2)

        self.btn = QPushButton("Transcribir")
        self.btn.clicked.connect(self.run)
        lay.addWidget(self.btn)

        self.out = QTextEdit(); self.out.setReadOnly(True); self.out.setPlaceholderText("Transcripción...")
        lay.addWidget(self.out)

    def _pick_audio(self):
        f, _ = QFileDialog.getOpenFileName(self, "Selecciona audio", "", "Audio (*.wav *.mp3 *.m4a *.flac);;Todos (*.*)")
        if f: self.audio_edit.setText(f)

    def run(self):
        try:
            from faster_whisper import WhisperModel
        except Exception:
            self.out.setPlainText("Instala faster-whisper y soundfile.")
            return

        audio = Path(self.audio_edit.text().strip())
        if not audio.exists():
            self.out.setPlainText("Elige un audio válido.")
            return

        # Preferir modelo local si está empaquetado
        model_dir = os.environ.get("WHISPER_MODEL_DIR")
        if model_dir and Path(model_dir).exists():
            model = WhisperModel(model_dir, device="auto", compute_type="auto")
        else:
            model = WhisperModel(self.model_size.currentText(), device="auto", compute_type="auto")

        segments, info = model.transcribe(str(audio), language=self.lang.text().strip(), vad_filter=True)
        lines = [s.text.strip() for s in segments]
        text = "\n".join(lines)
        self.out.setPlainText(text)
        out_txt = audio.with_suffix(".txt")
        out_txt.write_text(text, encoding="utf-8")

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ba2kit (GUI)")
        tabs = QTabWidget()
        tabs.addTab(CleanTab(), "🧼 Limpiar/validar")
        tabs.addTab(DiagnoseTab(), "🩺 Diagnosticar")
        tabs.addTab(CsvTab(), "📊 CSV")
        tabs.addTab(TranscribeTab(), "🎙️ Transcribir")
        self.setCentralWidget(tabs)
        self.resize(980, 700)

def main():
    app = QApplication(sys.argv)
    w = Main(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
