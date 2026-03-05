# metrics_logger.py
# Logger leve de eventos em JSONL para métricas de emergência
# Formato: uma linha JSON por evento, com timestamp ISO-8601

import os
import json
import tempfile
from collections import deque
from datetime import datetime, timezone

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

_LOG_MAX_LINES = 5000   # cap do arquivo; mantém as últimas N linhas


def log_event(event_type: str, payload: dict, log_file: str = "emergence.log"):
    """Registra um evento no log JSONL. Falha silenciosamente.
    Trunca o arquivo para _LOG_MAX_LINES quando ultrapassa esse limite.
    """
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **payload,
        }
        path = os.path.join(BASE_PATH, log_file)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Truncagem atômica: lê as últimas _LOG_MAX_LINES linhas via deque,
        # e se o arquivo estava maior, reescreve apenas essas.
        with open(path, "r", encoding="utf-8") as f:
            ultimas = list(deque(f, maxlen=_LOG_MAX_LINES))
        # deque só descarta linhas se havia mais que maxlen — usa o fato de
        # que len(ultimas) == _LOG_MAX_LINES implica que o arquivo tinha mais.
        # Para confirmar sem abrir uma terceira vez, estimamos pelo tamanho:
        if len(ultimas) == _LOG_MAX_LINES:
            dir_ = os.path.dirname(path) or "."
            fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.writelines(ultimas)
                os.replace(tmp, path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
    except Exception:
        pass


def read_recent(n: int = 50, log_file: str = "emergence.log") -> list:
    """Retorna os últimos N eventos do log."""
    try:
        path = os.path.join(BASE_PATH, log_file)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        events = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                events.append(json.loads(line))
        return events
    except Exception:
        return []


def read_window(window_seconds: float = 3600, log_file: str = "emergence.log") -> list:
    """Retorna eventos dentro da janela temporal (últimos N segundos)."""
    try:
        path = os.path.join(BASE_PATH, log_file)
        if not os.path.exists(path):
            return []
        cutoff = datetime.now(timezone.utc).timestamp() - window_seconds
        events = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["ts"]).timestamp()
                if ts >= cutoff:
                    events.append(entry)
        return events
    except Exception:
        return []
