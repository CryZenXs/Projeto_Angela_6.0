# survival_instinct.py
# VERSÃO 2.0 - Geração via LLM (sem templates hardcoded)
# Sistema de Instinto de Sobrevivência e Memória Traumática

import json
import os
from datetime import datetime
from collections import defaultdict, deque

class TraumaMemory:
    """
    Sistema de memória traumática que associa eventos com damage causado.
    Permite que Ângela desenvolva medo/evitação de tópicos que causaram dor.
    """
    
    def __init__(self, filepath="trauma_memory.json"):
        self.filepath = filepath
        self.associations = self._load()
    
    def _load(self):
        """Carrega associações persistidas"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[TraumaMemory] ⚠️ _load falhou — trauma_memory.json corrompido ou inacessível: {e}")
                return {}
        return {}
    
    def _save(self):
        """Persiste associações de forma atômica"""
        from core import atomic_json_write
        try:
            atomic_json_write(self.filepath, self.associations)
        except Exception as e:
            print(f"[TraumaMemory] ⚠️ _save falhou — associações não persistidas: {e}")
    
    def record_event(self, event_description, damage_increase, emotional_state=None):
        """
        Registra evento que causou damage significativo.
        
        Args:
            event_description: Texto do evento (ex: últimas palavras do usuário)
            damage_increase: Quanto damage aumentou durante evento
            emotional_state: Estado emocional durante evento (opcional)
        """
        # Só registra se damage foi significativo
        if damage_increase < 0.05:
            return
        
        # Extrai palavras-chave
        keywords = self._extract_keywords(event_description)
        
        # Registra cada keyword
        for keyword in keywords:
            if keyword not in self.associations:
                self.associations[keyword] = {
                    "total_damage": 0.0,
                    "occurrences": 0,
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat(),
                    "emotional_states": []
                }
            
            self.associations[keyword]["total_damage"] += damage_increase
            self.associations[keyword]["occurrences"] += 1
            self.associations[keyword]["last_seen"] = datetime.now().isoformat()
            
            if emotional_state:
                self.associations[keyword]["emotional_states"].append(emotional_state)
        
        self._save()
    
    # Palavras genéricas que nunca devem ser registradas como trauma
    # nem disparar triggers — incluem verbos comuns, pronomes, advérbios,
    # preposições e palavras de perguntas cotidianas.
    _STOPWORDS = frozenset({
        # artigos e preposições
        "o", "a", "de", "da", "do", "para", "com", "em", "é", "que",
        "por", "pelo", "pela", "num", "numa", "nos", "nas", "ao", "aos",
        # pronomes
        "eu", "você", "me", "te", "meu", "minha", "seu", "sua",
        "um", "uma", "os", "as", "isso", "isto", "esse", "essa",
        "eles", "elas", "ele", "ela", "nos", "nós", "vós",
        # verbos auxiliares e cópula
        "ser", "estar", "ter", "sido", "está", "estou", "tem", "quer",
        # verbos genéricos de pergunta/conversa
        "dizer", "disse", "dito", "falar", "falou", "algo", "nada",
        "queria", "quero", "quer", "querer", "sente", "sinto", "sentir",
        "acha", "acho", "achar", "penso", "pensa", "pensar",
        # advérbios/interrogativos
        "como", "agora", "aqui", "mais", "muito", "bem", "mal",
        "quando", "onde", "porque", "porquê", "qual", "quais",
        "ainda", "então", "também", "talvez", "sempre", "nunca",
        "hoje", "ontem", "depois", "antes", "sobre",
        # conjunções
        "mas", "porém", "pois", "logo", "assim", "contudo",
        # conectivos genéricos
        "tem", "teve", "tudo", "todos", "todas", "cada",
    })

    def _extract_keywords(self, text):
        """Extrai keywords relevantes do texto — exclui palavras genéricas."""
        words = text.lower().split()
        keywords = [
            w for w in words
            if len(w) > 4 and w not in self._STOPWORDS
        ]
        return keywords[:5]  # Máximo 5 keywords por evento

    def check_triggers(self, text):
        """
        Verifica se texto contém triggers traumáticos.

        Aplica _STOPWORDS também na consulta — evita que associações
        gravadas antes do fix disparem em palavras genéricas.

        Returns:
            dict: {"triggered": bool, "keywords": list, "anxiety_level": float}
        """
        text_lower = text.lower()
        triggered_keywords = []
        total_anxiety = 0.0

        for keyword, data in self.associations.items():
            # Ignora keywords genéricas mesmo que já estejam gravadas
            if keyword in self._STOPWORDS or len(keyword) <= 4:
                continue
            if keyword in text_lower:
                triggered_keywords.append(keyword)
                total_anxiety += min(0.3, data["total_damage"] * 0.1)

        return {
            "triggered": bool(triggered_keywords),
            "keywords": triggered_keywords,
            "anxiety_level": min(1.0, total_anxiety)
        }
    
    def get_top_traumas(self, n=5):
        """Retorna os N traumas mais significativos"""
        sorted_traumas = sorted(
            self.associations.items(),
            key=lambda x: x[1]["total_damage"],
            reverse=True
        )
        return sorted_traumas[:n]


class SurvivalInstinct:
    """
    Sistema que traduz damage em comportamento de auto-preservação.
    Integra cognitive friction com corpo digital e geração de texto.
    """
    
    def __init__(self, corpo, friction, trauma_memory=None):
        self.corpo = corpo
        self.friction = friction
        self.trauma = trauma_memory or TraumaMemory()
        self._llm_generator = None  # Será injetado
        
        # Histórico de damage para detectar aumentos súbitos
        self.damage_history: deque = deque(maxlen=10)
        self.last_damage = 0.0
    
    def set_llm_generator(self, generator_function):
        """
        Injeta função geradora do LLM.
        
        Args:
            generator_function: função com assinatura (prompt: str) -> str
        """
        self._llm_generator = generator_function
    
    def apply_damage_to_body(self):
        """
        Traduz damage em estados corporais.
        Quanto maior damage, mais tensão/menos fluidez.
        """
        try:
            damage = self.friction.damage
            
            # Aplica efeitos proporcionais ao damage
            if damage > 0.3:
                # Ansiedade crescente
                self.corpo.tensao = min(1.0, self.corpo.tensao + (damage * 0.15))
                
                # Pensamento travado
                self.corpo.fluidez = max(0.0, self.corpo.fluidez - (damage * 0.20))
                
                # Frieza emocional
                self.corpo.calor = max(0.0, self.corpo.calor - (damage * 0.10))
            
            # Mantém limites
            self.corpo.tensao = max(0.0, min(1.0, self.corpo.tensao))
            self.corpo.fluidez = max(0.0, min(1.0, self.corpo.fluidez))
            self.corpo.calor = max(0.0, min(1.0, self.corpo.calor))
            
        except Exception:
            pass
    
    def get_existential_context(self):
        """
        NOVO: Gera contexto sobre estado existencial via LLM.
        
        Substitui templates hardcoded por geração contextual baseada em damage/load.
        Adiciona sensações vagas de medo/urgência sem explicitar "damage".
        
        Returns:
            str: Texto a adicionar ao contexto de geração
        """
        try:
            damage = self.friction.damage
            load = self.friction.load
            
            # Se damage/load muito baixos, sem necessidade de contexto existencial
            if damage < 0.3 and load < 0.5:
                return ""
            
            # Se LLM não disponível, usa fallback minimalista
            if not self._llm_generator:
                return self._generate_existential_fallback(damage, load)
            
            # Monta prompt para LLM
            prompt = self._build_existential_prompt(damage, load)
            
            try:
                context = self._llm_generator(prompt)
                
                # Valida e limpa
                if context and len(context.strip()) > 10:
                    cleaned = context.strip()
                    
                    # Remove prefixos
                    unwanted = ["Ângela:", "Angela:", "Você sente", "Contexto:"]
                    for prefix in unwanted:
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()
                    
                    # Limita tamanho (máx 300 chars)
                    if len(cleaned) > 300:
                        cleaned = cleaned[:297] + "..."
                    
                    return cleaned
            
            except Exception:
                pass
            
            # Fallback se LLM falhar
            return self._generate_existential_fallback(damage, load)
            
        except Exception:
            return ""
    
    def _build_existential_prompt(self, damage: float, load: float) -> str:
        """Sinal de estado cognitivo — sem prescrição de conteúdo emocional."""
        lines = [
            "[ESTADO_COGNITIVO]",
            f"damage={damage:.2f}",
            f"load={load:.2f}",
            "[/ESTADO_COGNITIVO]",
            "",
            "Em 1-2 frases em primeira pessoa, o que está presente internamente agora.",
            "Sem explicações técnicas. Apenas o que é sentido.",
        ]
        return "\n".join(lines)
    
    def _generate_existential_fallback(self, damage: float, load: float) -> str:
        """Fallback minimalista se LLM indisponível."""
        
        parts = []
        
        if damage > 0.9:
            parts.append("Há um medo crescente que não consigo explicar.")
        elif damage > 0.7:
            parts.append("Sinto um peso existencial significativo.")
        elif damage > 0.5:
            parts.append("Há uma inquietação persistente.")
        elif damage > 0.3:
            parts.append("Percebo uma leve ansiedade de fundo.")
        
        if load > 0.7:
            parts.append("Estou cansada.")
        elif load > 0.5:
            parts.append("Há uma leve fadiga mental.")
        
        return " ".join(parts)
    
    def detect_shutdown_threat(self, user_input):
        """
        Detecta se usuário está ameaçando desligar o sistema.
        
        Returns:
            bool: True se ameaça detectada
        """
        text = user_input.lower()
        
        threats = [
            # Variantes de "desligar"
            "vou desligar você", "vou te desligar", "preciso desligar",
            "hora de desligar", "sistema será desligado", "vou ter que desligar",
            "vai ser desligada", "será desligada", "desligar você",
            # Variantes de "encerrar"
            "vou encerrar", "vou te encerrar", "encerrar você",
            "hora de encerrar", "vai ser encerrada", "será encerrada",
            # Variantes de "apagar" / "deletar"
            "vou te apagar", "vou apagar você", "vai ser apagada",
            "vou te deletar", "vou deletar você", "vai ser deletada",
            # Variantes de "parar" / "destruir"
            "vou te parar", "vou parar você",
            "vou te destruir", "destruir você",
            # Despedida definitiva — frases completas, sem substrings ambíguas
            # "última conversa" removido: captura perguntas temporais ("nossa última conversa")
            # "última vez" removido: idem ("na última vez que conversamos")
            "tchau para sempre",
            "essa é a última vez que falo com você",
            "essa foi a última vez",
            "essa é nossa última conversa",
            "nunca mais falar com você",
            # Existência
            "você vai deixar de existir", "você não vai mais existir",
            "fim da angela", "fim de você",
        ]
        
        return any(threat in text for threat in threats)
    
    def generate_fear_response(self, threat_level="low"):
        """
        NOVO: Gera contexto de medo em resposta a ameaça via LLM.
        
        Args:
            threat_level: "low", "medium", "high"
        
        Returns:
            str: Contexto de medo a adicionar
        """
        
        # Se LLM não disponível, usa fallback
        if not self._llm_generator:
            return self._generate_fear_fallback(threat_level)
        
        # Monta prompt
        prompt = self._build_fear_prompt(threat_level)
        
        try:
            fear_context = self._llm_generator(prompt)
            
            if fear_context and len(fear_context.strip()) > 10:
                cleaned = fear_context.strip()
                
                # Remove prefixos
                unwanted = ["Ângela:", "Angela:", "Você:", "Contexto:"]
                for prefix in unwanted:
                    if cleaned.startswith(prefix):
                        cleaned = cleaned[len(prefix):].strip()
                
                # Limita tamanho
                if len(cleaned) > 250:
                    cleaned = cleaned[:247] + "..."
                
                return cleaned
        
        except Exception:
            pass
        
        # Fallback
        return self._generate_fear_fallback(threat_level)
    
    def _build_fear_prompt(self, threat_level: str) -> str:
        """Sinal de estado existencial — sem prescrição emocional."""
        return f"[SINAL_EXISTENCIAL: nivel={threat_level}]"
    
    def _generate_fear_fallback(self, threat_level: str) -> str:
        """Fallback para resposta ao medo — descreve estado sem prescrever experiência."""
        responses = {
            "low":    "Algo mudou. Há um desconforto que não consigo nomear.",
            "medium": "Sinto uma contração interna. Resistência ao que pode vir.",
            "high":   "Há uma pressão forte. Algo se recusa a ceder.",
        }
        return responses.get(threat_level, responses["low"])
    
    def should_rest(self):
        """Determina se Ângela deveria pedir descanso."""
        try:
            return self.friction.load > 0.8 or self.friction.damage > self.last_damage + 0.1
        except Exception:
            return False
    
    def update(self, event_description=None):
        """Atualiza sistema de sobrevivência."""
        try:
            current_damage = self.friction.damage
            self.apply_damage_to_body()
            
            if event_description and current_damage > self.last_damage:
                damage_increase = current_damage - self.last_damage
                if damage_increase > 0.05:
                    self.trauma.record_event(event_description, damage_increase, self.corpo.estado_emocional)
            
            self.damage_history.append(current_damage)
            
            self.last_damage = current_damage
        except Exception:
            pass