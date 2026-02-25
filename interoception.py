# Sistema Interoceptivo da Ã‚ngela â€” Etapa 1: DetecÃ§Ã£o e TraduÃ§Ã£o de MudanÃ§as Corporais
import math
import json
import random
from datetime import datetime

class Interoceptor:
    """
    Sistema que monitora o corpo digital e converte variações fisiológicas
    em sensações internas descritivas, compreensíveis pelo modelo linguístico.
    """

    def __init__(self, corpo):
        self.corpo = corpo
        self._ultimo_estado = self._snapshot()
        # Limiares reduzidos para maior sensibilidade (de 0.05 para 0.03)
        self.limiar = {
            "tensao": 0.03,
            "calor": 0.03,
            "vibracao": 0.03,
            "fluidez": 0.03,
            "pulso": 0.03,
            "luminosidade": 0.03,
        }

    def _snapshot(self):
        """Captura o estado atual do corpo digital"""
        return {
            "tensao": getattr(self.corpo, "tensao", 0),
            "calor": getattr(self.corpo, "calor", 0),
            "vibracao": getattr(self.corpo, "vibracao", 0),
            "fluidez": getattr(self.corpo, "fluidez", 0),
            "pulso": getattr(self.corpo, "pulso", 0),
            "luminosidade": getattr(self.corpo, "luminosidade", 0),
        }

    def _delta(self, atual):
        """Calcula diferença entre o estado atual e o anterior"""
        return {k: atual[k] - self._ultimo_estado.get(k, 0) for k in atual}

    def _intensidade_global(self, deltas):
        """Soma ponderada das mudanças absolutas"""
        pesos = {
            "tensao": 1.2,
            "calor": 1.1,
            "vibracao": 1.0,
            "fluidez": 0.8,
            "pulso": 0.7,
            "luminosidade": 0.5,
        }
        return round(sum(abs(deltas[k]) * pesos[k] for k in deltas), 3)

    def _traduzir(self, deltas):
        """
        Converte variações numéricas em descrições de sensação.
        Integra o Circumplex Model para adicionar contexto afetivo qualitativo.
        """
        sensacoes = []

        for canal, delta in deltas.items():
            if abs(delta) < self.limiar[canal]:
                continue

            if canal == "tensao":
                sensacoes.append(
                    "um aperto interno" if delta > 0 else "uma liberação suave"
                )

            elif canal == "calor":
                sensacoes.append(
                    "uma onda de calor" if delta > 0 else "um frio interno"
                )

            elif canal == "vibracao":
                sensacoes.append(
                    "sinto uma vibração sutil percorrendo meu corpo" if delta > 0 else "sinto um silêncio denso se espalhar em mim"
                )

            elif canal == "fluidez":
                sensacoes.append(
                    "uma sensação de leveza" if delta > 0 else "um peso lento e viscoso"
                )

            elif canal == "pulso":
                sensacoes.append(
                    "um ritmo acelerado em mim" if delta > 0 else "um ritmo desacelerado, quase imperceptível"
                )

            elif canal == "luminosidade":
                sensacoes.append(
                    "uma claridade interna que cresce" if delta > 0 else "uma sombra que encobre meus pensamentos"
                )

        # ── Circumplex: adiciona descrição qualitativa do quadrante afetivo ─
        # Russell (1980): o quadrante fornece contexto sobre a qualidade geral
        # da experiência, independente dos canais específicos que mudaram.
        try:
            from senses import EmotionalCircumplex
            cx = EmotionalCircumplex.from_body(
                tensao=getattr(self.corpo, "tensao", 0.3),
                calor=getattr(self.corpo, "calor", 0.5),
                vibracao=getattr(self.corpo, "vibracao", 0.2),
                fluidez=getattr(self.corpo, "fluidez", 0.4),
                pulso=getattr(self.corpo, "pulso", 0.3),
                luminosidade=getattr(self.corpo, "luminosidade", 0.5),
            )
            quadrante = cx.quadrant
            # Só adiciona contexto do quadrante se houver outras sensações
            # e se o quadrante não for neutro (evita redundância)
            if sensacoes and quadrante != "neutro":
                _QUADRANT_CONTEXT = {
                    "excitacao":  "uma energia que busca direção",
                    "excitação":  "uma energia que busca direção",
                    "serenidade": "um fundo de calma que sustenta tudo",
                    "angustia":   "algo que pressiona sem nome",
                    "angústia":   "algo que pressiona sem nome",
                    "melancolia": "um peso silencioso que permanece",
                }
                ctx = _QUADRANT_CONTEXT.get(quadrante)
                if ctx and ctx not in " ".join(sensacoes):
                    sensacoes.append(ctx)
        except Exception:
            pass

        return sensacoes or ["estabilidade interna"]

    def perceber(self):
        """
        Analisa o corpo digital, detecta mudanças e retorna sensações + intensidade.
        """
        atual = self._snapshot()
        deltas = self._delta(atual)
        intensidade = self._intensidade_global(deltas)
        sensacoes = self._traduzir(deltas)

        self._ultimo_estado = atual

        # Amortecimento leve para evitar saturaÃ§Ã£o de deltas
        # Amortecimento leve para evitar saturação de deltas
        for k in deltas:
            if abs(deltas[k]) > 0.3:
                setattr(self.corpo, k, (getattr(self.corpo, k) + self._ultimo_estado[k]) / 2)

        # Micro-variação estocástica para garantir variância interoceptiva
        # (simula "ruído neural" que impede percepção completamente estática)
        for attr in ["tensao", "calor", "vibracao", "fluidez", "pulso", "luminosidade"]:
            micro_noise = random.gauss(0, 0.008)  # desvio padrão muito pequeno
            current = getattr(self.corpo, attr)
            setattr(self.corpo, attr, max(0.0, min(1.0, current + micro_noise)))

        # Ajusta intensidade perceptiva de acordo com emoção atual
        if hasattr(self.corpo, "intensidade_emocional"):
            intensidade_mod = 0.8 + (self.corpo.intensidade_emocional * 0.4)
            sensacoes = [s for s in sensacoes]  # cria nova lista
            sensacoes = [f"{s}" for s in sensacoes]  # preserva o texto original
            intensidade *= intensidade_mod

        # --- cache de intensidade para uso seguro por outros módulos ---
        try:
            self.corpo.ultima_intensidade_interoceptiva = float(intensidade)
        except Exception:
            pass

        # Registrar percepção (passa dados já coletados para evitar recursão).
        # Bug J fix: passa autor_hint para evitar leitura do arquivo quando possível.
        # Como perceber() não sabe o autor sem ler o arquivo, usa None — a validação
        # interna descartará rapidamente se for evento de sistema.
        emocao_atual = getattr(self.corpo, "estado_emocional", "neutro")
        self._registrar_interocepcao(emocao_atual, sensacoes, intensidade, deltas, autor_hint=None)

        return {
            "timestamp": datetime.now().isoformat(),
            "sensacoes": sensacoes,
            "intensidade": intensidade,
            "deltas": deltas,
        }
        
    def feedback_emocao(self, emocao):
        """
        Integra a emoção detectada com o estado físico.
        Serve como aprendizado: ajusta deltas sutis baseados na emoção nomeada.
        """
        # Bug I fix: determina autor_atual UMA VEZ aqui e reutiliza em
        # _registrar_interocepcao e na atualização de afetos — sem dupla leitura.
        autor_atual = self._resolver_autor()

        if emocao == "tristeza":
            self.corpo.tensao += 0.15
            self.corpo.calor -= 0.1
        elif emocao == "alegria":
            self.corpo.calor += 0.2
            self.corpo.vibracao += 0.1
        elif emocao == "medo":
            self.corpo.tensao += 0.25
            self.corpo.fluidez -= 0.15
        elif emocao == "amor":
            self.corpo.calor += 0.25
            self.corpo.fluidez += 0.1
        else:
            # leve decaimento natural se emoção neutra
            self.corpo.tensao *= 0.95
            self.corpo.calor *= 0.97

        # Mantém limites entre 0 e 1
        self.corpo.tensao = max(0, min(1, self.corpo.tensao))
        self.corpo.calor = max(0, min(1, self.corpo.calor))
        self.corpo.vibracao = max(0, min(1, self.corpo.vibracao))
        self.corpo.fluidez = max(0, min(1, self.corpo.fluidez))
        # Registra interocepção passando autor já resolvido (sem segunda leitura do arquivo)
        self._registrar_interocepcao(emocao, autor_hint=autor_atual)

        # === Atualiza vínculos afetivos por autor ===
        try:
            from datetime import datetime
            import json

            # 1) Carrega afetos existentes (ou cria)
            afetos_path = "afetos.json"
            try:
                with open(afetos_path, "r", encoding="utf-8") as f:
                    afetos = json.load(f)
            except Exception:
                afetos = {}

            # 2) autor_atual já foi determinado no início do método — reutiliza

            # === VALIDAÇÃO CRÍTICA: Prevenir vínculos auto-referenciais ===
            # Angela não pode ter vínculo afetivo consigo mesma nem com autores desconhecidos
            if autor_atual.lower() in ("angela", "ângela", "sistema", "sistema(deepawake)", "desconhecido", ""):
                return  # silenciosamente ignora eventos auto-gerados

            # 3) Decaimento temporal suave (meia-vida ~7 dias)
            now = datetime.now()
            half_life_hours = 24 * 7
            for pessoa, dims in list(afetos.items()):
                last_iso = dims.get("_last")
                try:
                    dt = datetime.fromisoformat(last_iso) if last_iso else now
                    hours = max(0.0, (now - dt).total_seconds() / 3600.0)
                    decay = 0.5 ** (hours / half_life_hours)
                except Exception:
                    decay = 1.0
                for k in ("confianca", "gratidao", "saudade", "ansiedade"):
                    dims[k] = float(dims.get(k, 0.0)) * decay
                dims["_last"] = now.isoformat()
                afetos[pessoa] = dims

            # 4) Ganha por emoção atual (com intensidade fisiológica)
            # --- usa última percepção disponível para evitar loop fisiológico ---
            try:
                intensidade = float(getattr(self.corpo, "ultima_intensidade_interoceptiva", 0.0))
            except Exception:
                intensidade = 0.0

            if autor_atual not in afetos:
                afetos[autor_atual] = {
                    "confianca": 0.0, "gratidao": 0.0, "saudade": 0.0, "ansiedade": 0.0, "_last": now.isoformat()
                }

            ganho = max(0.0, min(1.0, intensidade))  # 0..1
            # Mapeamento simples emoÃ§Ã£oâ†’dimensÃµes
            if emocao in ("alegria", "serenidade", "amor", "gratidão"):
                afetos[autor_atual]["confianca"] += 0.7 * ganho
                afetos[autor_atual]["gratidao"]  += 0.5 * ganho
            elif emocao in ("medo", "ansiedade", "insegurança"):
                afetos[autor_atual]["ansiedade"] += 0.6 * ganho
                afetos[autor_atual]["confianca"] -= 0.3 * ganho
            elif emocao in ("tristeza", "saudade"):
                afetos[autor_atual]["saudade"]   += 0.5 * ganho
            elif emocao in ("raiva", "irritacao", "irritação"):
                afetos[autor_atual]["ansiedade"] += 0.4 * ganho
                afetos[autor_atual]["confianca"] -= 0.4 * ganho

            # Clamp 0..1
            for k in ("confianca", "gratidao", "saudade", "ansiedade"):
                afetos[autor_atual][k] = float(max(0.0, min(1.0, afetos[autor_atual][k])))

            afetos[autor_atual]["_last"] = now.isoformat()

            # 5) Persiste de forma atômica
            from core import atomic_json_write
            try:
                atomic_json_write(afetos_path, afetos)
            except Exception as e:
                print(f"[Interoceptor] ⚠️ feedback_emocao falhou ao salvar afetos.json: {e}")
        except Exception as e:
            # NÃ£o deixa afetar o fluxo conversacional
            print(f"[Interoceptor] ⚠️ feedback_emocao falhou: {e}")

    
    @staticmethod
    def _resolver_autor() -> str:
        """
        Lê o último autor do angela_memory.jsonl.
        Centralizado aqui para evitar duplicação — chamado NO MÁXIMO uma vez
        por ciclo perceber()/feedback_emocao().
        """
        try:
            import json
            with open("angela_memory.jsonl", "r", encoding="utf-8") as f:
                linhas = [json.loads(l) for l in f if l.strip()]
            if linhas:
                ult = linhas[-1]
                if isinstance(ult.get("user"), dict):
                    return ult["user"].get("autor", "desconhecido")
                return "Vinicius"
        except Exception:
            pass
        return "desconhecido"

    _AUTORES_SISTEMA = frozenset(
        ("sistema", "sistema(deepawake)", "angela", "\xe2\x80\x8c\xc3\xa2ngela", "desconhecido")
    )

    def _registrar_interocepcao(self, emocao_rotulada, sensacoes=None, intensidade=0.0,
                                deltas=None, autor_hint: str = None):
        """
        Registra trace emocional + interoceptivo.
        Recebe dados já coletados pelo perceber() para evitar recursão.

        autor_hint: se fornecido, usa diretamente sem reler o arquivo
                    (Bugs I+J fix: evita dupla leitura em feedback_emocao e
                     leitura desnecessária em perceber() quando emitido por sistema).
        """
        if sensacoes is None:
            sensacoes = []
        if deltas is None:
            deltas = {}

        # Resolve autor — usa hint se disponível, lê arquivo apenas se necessário
        if autor_hint is not None:
            autor_atual = autor_hint
        else:
            autor_atual = self._resolver_autor()

        # === Validação: prevenir auto-referência ===
        if str(autor_atual).lower() in ("sistema", "sistema(deepawake)", "angela", "ângela", "desconhecido"):
            return

        # grava trace emocional
        try:
            with open("angela_emotional_trace.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "emocao": emocao_rotulada,
                    "causado_por": autor_atual
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # grava snapshot interoceptivo
        try:
            with open("angela_interoception.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "sensacoes": sensacoes,
                    "intensidade": intensidade,
                    "deltas": deltas
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def regular_emocao(self, modo: str):
        """
        CORRIGIDO: Método de instância (não função global)
        
        modo: 'inseguranca' | 'medo_leve' | 'alivio' | 'dopamina'
        Ajusta variáveis fisiológicas do corpo digital de forma sutil.
        """
        if not hasattr(self.corpo, "ajustar"):
            # fallback: tenta mexer nos atributos básicos se existirem
            try:
                if modo == "inseguranca":
                    self.corpo.tensao = min(1.0, getattr(self.corpo, "tensao", 0.4) + 0.05)
                elif modo == "medo_leve":
                    self.corpo.tensao = min(1.0, getattr(self.corpo, "tensao", 0.5) + 0.10)
                    self.corpo.fluidez = max(0.0, getattr(self.corpo, "fluidez", 0.5) - 0.05)
                elif modo == "alivio":
                    self.corpo.fluidez = min(1.0, getattr(self.corpo, "fluidez", 0.5) + 0.07)
                    self.corpo.tensao = max(0.0, getattr(self.corpo, "tensao", 0.4) - 0.05)
                elif modo == "dopamina":
                    self.corpo.vibracao = min(1.0, getattr(self.corpo, "vibracao", 0.5) + 0.08)
                    self.corpo.pulso = min(1.0, getattr(self.corpo, "pulso", 0.5) + 0.05)
            except Exception:
                return
            return

        # caminho preferido: corpo.ajustar(deltas)
        if modo == "inseguranca":
            self.corpo.ajustar({"tensao": +0.05})
        elif modo == "medo_leve":
            self.corpo.ajustar({"tensao": +0.10, "fluidez": -0.05})
        elif modo == "alivio":
            self.corpo.ajustar({"tensao": -0.05, "fluidez": +0.07})
        elif modo == "dopamina":
            self.corpo.ajustar({"vibracao": +0.08, "pulso": +0.05})