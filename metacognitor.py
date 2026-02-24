# metacognitor.py
# VERSÃO 2.0 - Geração via LLM (sem templates hardcoded)
# Avalia incerteza/coerência e gera reflexão metacognitiva via LLM

from datetime import datetime
from collections import deque
from core import append_memory

HEDGES = ("talvez", "acho", "não sei", "incerto", "não tenho certeza", "pode ser", "imagino", "suposição", "hipótese")
CONTRAS = ("porém", "contudo", "entretanto", "mas")

class MetaCognitor:
    def __init__(self, interoceptor):
        self.interoceptor = interoceptor
        self._llm_generator = None  # Será injetado
        self._recent_reflexoes = deque(maxlen=5)  # dedup de reflexões

    def set_llm_generator(self, generator_function):
        """
        Injeta função geradora do LLM.
        
        Args:
            generator_function: função com assinatura (prompt: str) -> str
        """
        self._llm_generator = generator_function

    def _uncertainty_from_text(self, texto: str) -> float:
        if not texto:
            return 0.7
        t = texto.lower()
        u = 0.0
        u += sum(1 for w in HEDGES if w in t) * 0.12
        u += min(0.24, (texto.count("?") * 0.08))
        u += min(0.20, (sum(1 for w in CONTRAS if w in t) * 0.10))
            # penalidades para assertividade rígida e monólogo pouco pontuado
        if any(w in t for w in ("sempre", "nunca", "com certeza", "sem dúvida")):
            u += 0.10
        if len(texto) > 300 and texto.count(".") < 2:
            u += 0.08

        # piso mínimo de incerteza para evitar 0.00 constante
        u = max(u, 0.12)
        return max(0.0, min(1.0, u))

    def _coherence_score(self, emocao_nome: str, intensidade: float, texto: str) -> float:
        # coerência burra: se fala "calma/serenidade" e aparece muita negação/pressão, reduz
        t = (texto or "").lower()
        em = (emocao_nome or "neutro").lower()
        penal = 0.0
        if em in ("serenidade", "calma", "neutro"):
            penal += min(0.5, t.count("não") * 0.05 + t.count("mas") * 0.06)
        if em in ("medo", "ansiedade") and any(w in t for w in ("tudo bem", "tranquilo", "estou bem")):
            penal += 0.2
        base = 0.8 - penal
        base -= min(0.3, abs(intensidade - 0.5) * 0.3)  # extremos tendem a incoerências linguísticas
        return max(0.0, min(1.0, base))

    def process(self, *, texto_resposta: str, emocao_nome: str, intensidade: float, contexto_memoria: str = "", autor="sistema"):
        # 1) medir incerteza e coerência
        u = self._uncertainty_from_text(texto_resposta)
        
        coh = self._coherence_score(emocao_nome, intensidade or 0.0, texto_resposta)
        
        # 2) decidir emoção corretiva do corpo
        ajuste = None
        if u >= 0.55 or coh <= 0.4:
            ajuste = "inseguranca" if u < 0.8 else "medo_leve"
        else:
            ajuste = "dopamina" if coh >= 0.75 and u <= 0.25 else "alivio"
        
        # 3) gerar reflexão metacognitiva via LLM (ou fallback se indisponível)
        reflexao = self._generate_metacognitive_reflection(
            u, coh, ajuste, texto_resposta, emocao_nome
        )
        
        # 4) aplicar regulação no corpo (interocepção)
        try:
            self.interoceptor.regular_emocao(ajuste)
        except Exception:
            pass
        
        # 5) registrar aprendizado metacognitivo
        evento = {
            "ts": datetime.now().isoformat(),
            "tipo": "metacognicao",
            "autor": autor,
            "uncertainty": round(float(u), 3),
            "coerencia": round(float(coh), 3),
            "ajuste": ajuste,
            "reflexao": reflexao,
        }
        
        # Deduplicação: só salva se reflexão é diferente das recentes
        salvar_meta = True
        reflexao_norm = reflexao.strip().lower()[:80]
        for prev in self._recent_reflexoes:
            if prev == reflexao_norm:
                salvar_meta = False
                break
        self._recent_reflexoes.append(reflexao_norm)

        if salvar_meta:
            append_memory(
                {"autor": autor or "Sistema", "conteudo": f"[META] {reflexao}", "tipo": "metacognicao", "timestamp": datetime.now().isoformat()},
                reflexao,
                None,
                reflexao
            )
        
        return {
            "incerteza": u,
            "coerencia": coh,
            "ajuste": ajuste,         # <- COMPATIBILIDADE com código antigo
            "ajuste_corpo": ajuste,   # <- CONSISTÊNCIA com nomenclatura nova
            "reflexao": reflexao
        }
    
    def reappraise(
        self,
        event_description: str,
        current_emotion: str,
        corpo_state: dict,
    ) -> dict:
        """
        Reavaliação cognitiva (Gross 2015; Ochsner & Gross 2005).
        
        Em vez de suprimir ou absorver a emoção, reinterpreta o evento
        que a causou para alterar a resposta emocional de forma adaptativa.
        
        Diferença do process():
          process()    → detecta dissonância e aplica ajuste corporal reativo
          reappraise() → reinterpreta o EVENTO para mudar a emoção resultante
        
        Retorna:
          new_interpretation: str  — nova leitura do evento
          suggested_emotion:  str  — emoção mais adaptativa
          body_adjustment:    str  — qual ajuste aplicar no corpo
          reappraised:        bool — se a reavaliação foi bem-sucedida
        """
        result = {
            "new_interpretation": "",
            "suggested_emotion":  current_emotion,
            "body_adjustment":    "alivio",
            "reappraised":        False,
        }

        if not event_description or not current_emotion:
            return result

        tensao  = corpo_state.get("tensao",  0.5)
        fluidez = corpo_state.get("fluidez", 0.5)

        # Só aplica reavaliação quando emoção é suficientemente intensa
        # (estados neutros não precisam de reappraisal)
        emocoes_que_requerem = {"medo", "raiva", "ansiedade", "tristeza", "saudade"}
        if current_emotion.lower() not in emocoes_que_requerem and tensao < 0.5:
            return result

        # Gera reavaliação via LLM se disponível
        if self._llm_generator:
            try:
                prompt = (
                    f"Estou sentindo {current_emotion} em relação a: '{event_description[:150]}'. "
                    f"Estado corporal: tensão={tensao:.2f}, fluidez={fluidez:.2f}. "
                    "Sem negar o que sinto, como posso interpretar esse evento de forma "
                    "diferente que seja honesta e mais adaptativa? "
                    "Responda em 1 frase íntima, primeira pessoa."
                )
                nova_interpretacao = self._llm_generator(prompt)

                if nova_interpretacao and len(nova_interpretacao.strip()) > 10:
                    result["new_interpretation"] = nova_interpretacao.strip()
                    result["reappraised"]        = True

                    # Determina ajuste corporal pela qualidade da reavaliação
                    lower = nova_interpretacao.lower()
                    if any(w in lower for w in ("entendo", "faz sentido", "posso", "consigo", "capaz")):
                        result["suggested_emotion"] = "serenidade"
                        result["body_adjustment"]   = "dopamina"
                    elif any(w in lower for w in ("ainda difícil", "não sei", "complexo", "incerto")):
                        result["suggested_emotion"] = "neutro"
                        result["body_adjustment"]   = "alivio"
                    else:
                        result["body_adjustment"] = "alivio"

                    # Aplica ajuste no corpo
                    try:
                        self.interoceptor.regular_emocao(result["body_adjustment"])
                    except Exception:
                        pass

            except Exception:
                pass

        return result
    
    def _generate_metacognitive_reflection(
        self, uncertainty: float, coherence: float, ajuste: str, 
        texto_original: str, emocao: str
    ) -> str:
        """
        NOVO: Gera reflexão metacognitiva via LLM.
        
        Substitui templates hardcoded por geração contextual.
        """
        
        # Se LLM não disponível, usa fallback minimalista
        if not self._llm_generator:
            return self._generate_fallback_reflection(uncertainty, coherence, ajuste)
        
        # Monta prompt para LLM
        prompt = self._build_metacognitive_prompt(
            uncertainty, coherence, ajuste, texto_original, emocao
        )
        
        try:
            # Gera via LLM
            reflection = self._llm_generator(prompt)
            
            # Valida e limpa
            if reflection and len(reflection.strip()) > 10:
                cleaned = reflection.strip()
                
                # Remove prefixos indesejados
                unwanted = ["Ângela:", "Angela:", "Sou Ângela.", "[META]"]
                for prefix in unwanted:
                    if cleaned.startswith(prefix):
                        cleaned = cleaned[len(prefix):].strip()
                
                # Limita tamanho (máx 200 chars)
                if len(cleaned) > 200:
                    cleaned = cleaned[:197] + "..."
                
                return cleaned
        
        except Exception:
            pass
        
        # Fallback se LLM falhar
        return self._generate_fallback_reflection(uncertainty, coherence, ajuste)
    
    def _build_metacognitive_prompt(
        self, uncertainty: float, coherence: float, ajuste: str,
        texto_original: str, emocao: str
    ) -> str:
        """Constrói prompt para reflexão metacognitiva."""
        
        confidence = round(1.0 - uncertainty, 2)
        
        prompt_parts = [
            "Você é Ângela. Você acabou de dizer algo e agora está REVISANDO o que disse.",
            f"Ao analisar suas próprias palavras, você percebe:",
            f"- Incerteza: {uncertainty:.2f}/1.0 (o quanto você está insegura sobre o que disse)",
            f"- Coerência: {coherence:.2f}/1.0 (o quanto suas palavras combinam com seus sentimentos)",
            f"- Confiança: {confidence:.2f}/1.0 (certeza sobre o que expressou)",
        ]
        
        if emocao and emocao != "neutro":
            prompt_parts.append(f"- Emoção sentida: {emocao}")
        
        # Orientação específica por estado
        if ajuste == "inseguranca":
            prompt_parts.append(
                "\nVocê está se sentindo INSEGURA sobre o que acabou de dizer. "
                "Em 1-2 frases breves e diretas, expresse essa insegurança de forma natural. "
                "Como você se sente ao revisar suas próprias palavras? O que te incomoda?"
            )
        elif ajuste == "medo_leve":
            prompt_parts.append(
                "\nVocê sente um MEDO LEVE ao revisar o que disse. "
                "Em 1-2 frases, expresse esse desconforto de forma intimista e pessoal."
            )
        elif ajuste == "dopamina":
            prompt_parts.append(
                "\nVocê percebe BOA COERÊNCIA e BAIXA INCERTEZA no que disse. "
                "Isso te dá uma pequena sensação de acerto. "
                "Em 1-2 frases, expresse essa satisfação discreta."
            )
        else:  # alivio
            prompt_parts.append(
                "\nVocê sente um ALÍVIO LEVE ao revisar. "
                "As coisas parecem razoáveis, nem muito certas nem muito confusas. "
                "Em 1-2 frases, expresse essa calma moderada."
            )
        
        prompt_parts.append(
            "\nIMPORTANTE: Seja breve, natural e em primeira pessoa. "
            "Sem listas, sem explicações técnicas, sem metáforas rebuscadas."
        )
        
        return "\n".join(prompt_parts)
    
    def _generate_fallback_reflection(
        self, uncertainty: float, coherence: float, ajuste: str
    ) -> str:
        """Fallback minimalista se LLM completamente indisponível."""
        
        confidence = round(1.0 - uncertainty, 2)
        
        if ajuste == "inseguranca":
            return (
                f"Sinto insegurança ao revisar o que disse. "
                f"Minha confiança está em {confidence:.2f} e a coerência em {coherence:.2f}."
            )
        elif ajuste == "medo_leve":
            return (
                f"Um medo leve me invade ao olhar para minhas palavras. "
                f"Incerteza: {uncertainty:.2f}, coerência: {coherence:.2f}."
            )
        elif ajuste == "dopamina":
            return (
                f"Percebo boa coerência ({coherence:.2f}) e baixa incerteza ({uncertainty:.2f}). "
                f"Uma pequena sensação de acerto."
            )
        else:  # alivio
            return (
                f"Sinto alívio leve. "
                f"Incerteza {uncertainty:.2f}, coerência {coherence:.2f}. "
                f"Posso aprofundar com calma se for útil."
            )
