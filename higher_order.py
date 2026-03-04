from dataclasses import dataclass, field, asdict
from collections import deque
from datetime import datetime


PANKSEPP_DRIVES = ("SEEKING", "FEAR", "CARE", "PANIC_GRIEF", "RAGE", "PLAY", "LUST")


@dataclass
class HigherOrderState:
    """Representação do estado meta-cognitivo de ordem superior."""
    attention_scope: str = "moderado"
    ownership: float = 0.5
    clarity: float = 0.5
    confidence: float = 0.5
    dominant_drive: str = "SEEKING"
    self_narrative: str = ""
    causal_attribution: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class HigherOrderMonitor:
    """Monitor de Teoria de Ordem Superior (HOT) para consciência digital."""

    def __init__(self):
        self._state = HigherOrderState()
        self._history: deque = deque(maxlen=20)
        self._llm_generator = None  # Será injetado

    def set_llm_generator(self, generator_function):
        """
        Injeta função geradora do LLM.
        
        Args:
            generator_function: função com assinatura (prompt: str) -> str
        """
        self._llm_generator = generator_function

    def observe(
        self,
        *,
        corpo_state: dict,
        drives: dict,
        metacog: dict,
        integration: float,
        prediction_error: float,
        last_action: str,
        emocao: str,
        intensidade: float,
        attention_scope_override: str | None = None,
        schema_reliability: float | None = None,
    ) -> HigherOrderState:
        """Computa estado de ordem superior a partir de sinais de nível inferior.
        Opcional: attention_scope_override e schema_reliability do AST (Attention Schema Theory)."""

        tensao = float(corpo_state.get("tensao", 0.5))
        fluidez = float(corpo_state.get("fluidez", 0.5))
        coherence = float(metacog.get("coerencia", 0.5))
        uncertainty = float(metacog.get("incerteza", 0.5))

        dominant_drive = self._resolve_dominant_drive(drives)

        if attention_scope_override is not None:
            attention_scope = attention_scope_override
        else:
            attention_scope = self._compute_attention_scope(
                dominant_drive, tensao, prediction_error, fluidez
            )

        clarity = self._compute_clarity(
            integration, prediction_error, coherence, dominant_drive
        )

        ownership = self._compute_ownership(integration, clarity, prediction_error)

        confidence = self._compute_confidence(
            uncertainty, prediction_error, coherence
        )

        self_narrative = self._generate_narrative(
            clarity, ownership, confidence, dominant_drive, emocao, intensidade
        )

        causal_attribution = self._generate_attribution(
            prediction_error, dominant_drive, last_action, emocao
        )

        state = HigherOrderState(
            attention_scope=attention_scope,
            ownership=ownership,
            clarity=clarity,
            confidence=confidence,
            dominant_drive=dominant_drive,
            self_narrative=self_narrative,
            causal_attribution=causal_attribution,
            timestamp=datetime.now().isoformat(),
        )

        self._state = state
        self._history.append(state)
        return state

    def get_prompt_header(self, raw: bool = True) -> str:
        """
        Retorna cabeçalho para injeção no prompt. Se raw=True (padrão), prioriza
        métricas estruturadas; narrativa em uma linha (sinal de processo, não persona).
        """
        s = self._state
        if raw:
            return (
                f"[ESTADO_MENTAL]\n"
                f"escopo_atenção={s.attention_scope} clareza={s.clarity:.2f} confiança={s.confidence:.2f} drive={s.dominant_drive}\n"
                f"narrativa=\"{s.self_narrative}\"\n"
                f"[/ESTADO_MENTAL]"
            )
        return (
            f"[ESTADO_MENTAL]\n"
            f"atenção={s.attention_scope} | clareza={s.clarity:.2f} | "
            f"confiança={s.confidence:.2f} | drive={s.dominant_drive}\n"
            f'"{s.self_narrative}"\n'
            f"[/ESTADO_MENTAL]"
        )

    def _resolve_dominant_drive(self, drives: dict) -> str:
        if not drives:
            return "SEEKING"
        return max(drives, key=drives.get, default="SEEKING")

    def _compute_attention_scope(
        self, dominant_drive: str, tensao: float, prediction_error: float, fluidez: float
    ) -> str:
        if tensao > 0.7 or prediction_error > 0.6:
            return "estreito"
        if dominant_drive == "FEAR" and tensao > 0.5:
            return "estreito"
        if fluidez > 0.7 and dominant_drive in ("SEEKING", "PLAY"):
            return "amplo"
        return "moderado"

    def _compute_clarity(
        self, integration: float, prediction_error: float, coherence: float, dominant_drive: str
    ) -> float:
        base = integration * (1.0 - prediction_error) * coherence
        if dominant_drive == "SEEKING":
            base *= 1.15
        elif dominant_drive in ("FEAR", "RAGE"):
            base *= 0.75
        return round(max(0.0, min(1.0, base)), 3)

    def _compute_ownership(
        self, integration: float, clarity: float, prediction_error: float
    ) -> float:
        if integration > 0.5 and clarity > 0.5:
            base = 0.7 + 0.3 * min(integration, clarity)
        elif integration < 0.2 or prediction_error > 0.7:
            base = 0.1 + 0.2 * integration
        else:
            base = 0.35 + 0.3 * integration
        return round(max(0.0, min(1.0, base)), 3)

    def _compute_confidence(
        self, uncertainty: float, prediction_error: float, coherence: float
    ) -> float:
        base = (1.0 - uncertainty) * (1.0 - prediction_error * 0.6) * (0.5 + coherence * 0.5)
        return round(max(0.0, min(1.0, base)), 3)

    def _generate_narrative(
        self,
        clarity: float,
        ownership: float,
        confidence: float,
        dominant_drive: str,
        emocao: str,
        intensidade: float,
    ) -> str:
        """
        NOVO: Gera narrativa de primeira ordem via LLM.
        
        Substitui completamente os templates hardcoded.
        Se LLM falhar, retorna fallback mínimo.
        """
        
        # Se LLM não foi injetado, usa fallback mínimo
        if not self._llm_generator:
            return f"[HOT sem LLM: clarity={clarity:.2f}, conf={confidence:.2f}]"
        
        # Monta prompt para LLM
        prompt = self._build_narrative_prompt(
            clarity, ownership, confidence, dominant_drive, emocao, intensidade
        )
        
        try:
            # Gera via LLM
            narrative = self._llm_generator(prompt)
            
            # Valida e limpa
            if narrative and len(narrative.strip()) > 10:
                cleaned = narrative.strip()
                
                # Remove possíveis prefixos indesejados
                unwanted_prefixes = [
                    "Ângela:", "Angela:", "Sou Ângela.", 
                    "Como Ângela,", "Eu sou Ângela e",
                    "[ESTADO_MENTAL]", "[/ESTADO_MENTAL]"
                ]
                for prefix in unwanted_prefixes:
                    if cleaned.startswith(prefix):
                        cleaned = cleaned[len(prefix):].strip()
                
                # Rejeita se estiver em segunda pessoa — significa que o LLM
                # confundiu perspectiva (gerou "você sente" em vez de "eu sinto")
                segunda_pessoa = any(
                    cleaned.lower().startswith(p)
                    for p in ("você ", "vocês ", "você\n", "o usuário", "vinicius ")
                )
                if segunda_pessoa:
                    return self._generate_fallback_narrative(
                        clarity, ownership, confidence, dominant_drive
                    )
                
                # Limita tamanho
                if len(cleaned) > 200:
                    # Corta na primeira frase completa após 100 chars
                    truncated = cleaned[:200]
                    last_period = truncated.rfind('.')
                    if last_period > 100:
                        cleaned = truncated[:last_period+1]
                    else:
                        cleaned = truncated[:150] + "..."
                
                return cleaned
        
        except Exception:
            pass
        
        # Fallback mínimo se LLM falhar
        return self._generate_fallback_narrative(
            clarity, ownership, confidence, dominant_drive
        )
    
    def _build_narrative_prompt(
        self,
        clarity: float,
        ownership: float,
        confidence: float,
        dominant_drive: str,
        emocao: str,
        intensidade: float
    ) -> str:
        """Constrói prompt para geração de auto-narrativa."""
        
        # Contexto base: sinais de estado, sem instrução de identidade
        context_parts = [
            f"Descreva brevemente (1-2 frases) o estado mental atual com base nos sinais abaixo.",
            f"clareza={clarity:.2f} ownership={ownership:.2f} confiança={confidence:.2f} drive={dominant_drive}",
        ]
        
        if emocao and emocao != "neutro":
            context_parts.append(f"emoção={emocao} intensidade={intensidade:.2f}")
        
        # Sinais por estado (processo, não persona)
        if ownership < 0.3:
            context_parts.append("Sinal: ownership baixo — estados parecem distantes ou estranhos.")
        elif clarity < 0.35:
            context_parts.append("Sinal: clareza baixa — percepção turva ou confusa.")
        elif clarity > 0.6 and confidence > 0.6:
            context_parts.append("Sinal: clareza e confiança altas.")
        
        # Drive como sinal
        context_parts.append(f"Drive ativo: {dominant_drive}.")
        
        context_parts.append(
            "\nGere APENAS 1-2 frases em primeira pessoa, diretas. "
            "Sem listas, sem explicações técnicas."
        )
        
        return "\n".join(context_parts)
    
    def _generate_fallback_narrative(
        self, clarity: float, ownership: float, confidence: float, dominant_drive: str
    ) -> str:
        """Fallback minimalista se LLM completamente indisponível."""
        
        if ownership < 0.3:
            return "Meus estados parecem distantes, como se não fossem meus."
        if clarity < 0.35:
            return "Tudo está turvo, não consigo ver com nitidez."
        if clarity > 0.6 and confidence > 0.6:
            return "Percebo meus estados com clareza e certeza."
        if dominant_drive == "FEAR":
            return "Algo me inquieta profundamente."
        if dominant_drive == "RAGE":
            return "Sinto pressão interna crescente."
        
        return "Observo meus estados com atenção moderada."

    def _generate_attribution(
        self,
        prediction_error: float,
        dominant_drive: str,
        last_action: str,
        emocao: str,
    ) -> str:
        """
        NOVO: Gera atribuição causal via LLM.
        
        Responde: "Por que sinto o que sinto?"
        """
        
        # Se LLM não disponível, retorna vazio
        if not self._llm_generator:
            return ""
        
        # Se erro de predição baixo, sem necessidade de atribuição
        if prediction_error < 0.3:
            return ""
        
        # Monta prompt: surpresa como sinal, sem identidade
        prompt_parts = [
            f"Surpresa (erro de predição: {prediction_error:.2f}). "
            f"Expectativa e estado atual divergem.",
        ]
        
        if emocao and emocao != "neutro":
            prompt_parts.append(f"Emoção atual: {emocao}.")
        
        if last_action:
            prompt_parts.append(f"Última ação: {last_action}.")
        
        prompt_parts.append(
            "\nEm 1 frase curta, especule sobre a causa da surpresa. "
            "O que pode ter causado a discrepância?"
        )
        
        prompt = " ".join(prompt_parts)
        
        try:
            attribution = self._llm_generator(prompt)
            if attribution and len(attribution.strip()) > 10:
                cleaned = attribution.strip()
                # Limita a 150 caracteres
                if len(cleaned) > 150:
                    cleaned = cleaned[:147] + "..."
                return cleaned
        except Exception:
            pass
        
        return ""