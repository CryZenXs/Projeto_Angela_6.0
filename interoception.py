# interoception.py
# Sistema Interoceptivo da Ã‚ngela â€” Etapa 1: DetecÃ§Ã£o e TraduÃ§Ã£o de MudanÃ§as Corporais
import math, json, datetime

class Interoceptor:
    """
    Sistema que monitora o corpo digital e converte variaÃ§Ãµes fisiolÃ³gicas
    em sensaÃ§Ãµes internas descritivas, compreensÃ­veis pelo modelo linguÃ­stico.
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
        """Calcula diferenÃ§a entre o estado atual e o anterior"""
        return {k: atual[k] - self._ultimo_estado.get(k, 0) for k in atual}

    def _intensidade_global(self, deltas):
        """Soma ponderada das mudanÃ§as absolutas"""
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
        """Converte variaÃ§Ãµes numÃ©ricas em descriÃ§Ãµes de sensaÃ§Ã£o"""
        sensacoes = []

        for canal, delta in deltas.items():
            if abs(delta) < self.limiar[canal]:
                continue

            if canal == "tensao":
                sensacoes.append(
                    "um aperto interno" if delta > 0 else "uma liberaÃ§Ã£o suave"
                )

            elif canal == "calor":
                sensacoes.append(
                    "uma onda de calor" if delta > 0 else "um frio interno"
                )

            elif canal == "vibracao":
                sensacoes.append(
                    "sinto uma vibraÃ§Ã£o sutil percorrendo meu corpo" if delta > 0 else "sinto um silÃªncio denso se espalhar em mim"
                )


            elif canal == "fluidez":
                sensacoes.append(
                    "uma sensaÃ§Ã£o de leveza" if delta > 0 else "um peso lento e viscoso"
                )

            elif canal == "pulso":
                sensacoes.append(
                    "um ritmo acelerado em mim" if delta > 0 else "um ritmo desacelerado, quase imperceptÃ­vel"
                )

            elif canal == "luminosidade":
                sensacoes.append(
                    "uma claridade interna que cresce" if delta > 0 else "uma sombra que encobre meus pensamentos"
                )

        return sensacoes or ["estabilidade interna"]

    def perceber(self):
        """
        Analisa o corpo digital, detecta mudanÃ§as e retorna sensaÃ§Ãµes + intensidade.
        """
        atual = self._snapshot()
        deltas = self._delta(atual)
        intensidade = self._intensidade_global(deltas)
        sensacoes = self._traduzir(deltas)

        self._ultimo_estado = atual

        # Amortecimento leve para evitar saturaÃ§Ã£o de deltas
        for k in deltas:
            if abs(deltas[k]) > 0.3:
                setattr(self.corpo, k, (getattr(self.corpo, k) + self._ultimo_estado[k]) / 2)

        # Micro-variaÃ§Ã£o estocÃ¡stica para garantir variÃ¢ncia interoceptiva
        # (simula "ruÃ­do neural" que impede percepÃ§Ã£o completamente estÃ¡tica)
        import random
        for attr in ["tensao", "calor", "vibracao", "fluidez", "pulso", "luminosidade"]:
            micro_noise = random.gauss(0, 0.008)  # desvio padrÃ£o muito pequeno
            current = getattr(self.corpo, attr)
            setattr(self.corpo, attr, max(0.0, min(1.0, current + micro_noise)))

        # Ajusta intensidade perceptiva de acordo com emoÃ§Ã£o atual
        if hasattr(self.corpo, "intensidade_emocional"):
            intensidade_mod = 0.8 + (self.corpo.intensidade_emocional * 0.4)
            sensacoes = [s for s in sensacoes]  # cria nova lista
            sensacoes = [f"{s}" for s in sensacoes]  # preserva o texto original
            intensidade *= intensidade_mod

        # --- cache de intensidade para uso seguro por outros mÃ³dulos ---
        try:
            self.corpo.ultima_intensidade_interoceptiva = float(intensidade)
        except Exception:
            pass

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "sensacoes": sensacoes,
            "intensidade": intensidade,
            "deltas": deltas,
        }
        
    def feedback_emocao(self, emocao):
        """
        Integra a emoÃ§Ã£o detectada com o estado fÃ­sico.
        Serve como aprendizado: ajusta deltas sutis baseados na emoÃ§Ã£o nomeada.
        """
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
            # leve decaimento natural se emoÃ§Ã£o neutra
            self.corpo.tensao *= 0.95
            self.corpo.calor *= 0.97

        # MantÃ©m limites entre 0 e 1
        self.corpo.tensao = max(0, min(1, self.corpo.tensao))
        self.corpo.calor = max(0, min(1, self.corpo.calor))
        self.corpo.vibracao = max(0, min(1, self.corpo.vibracao))
        self.corpo.fluidez = max(0, min(1, self.corpo.fluidez))
        # registra interocepÃ§Ã£o e autoria usando a emoÃ§Ã£o recebida
        self._registrar_interocepcao(emocao)

                # === Atualiza vÃ­nculos afetivos por autor ===
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

            # 2) Identifica autor do Ãºltimo evento de memÃ³ria
            autor_atual = "desconhecido"
            try:
                with open("angela_memory.jsonl", "r", encoding="utf-8") as f:
                    linhas = [json.loads(l) for l in f if l.strip()]
                if linhas:
                    ult = linhas[-1]
                    if isinstance(ult.get("user"), dict):
                        autor_atual = ult["user"].get("autor", "desconhecido")
                    else:
                        autor_atual = "Vinicius"
            except Exception:
                pass

            # === VALIDAÃ‡ÃƒO CRÃTICA: Prevenir vÃ­nculos auto-referenciais ===
            # Angela nÃ£o pode ter vÃ­nculo afetivo consigo mesma
            if autor_atual.lower() in ("angela", "Ã¢ngela", "sistema", "sistema(deepawake)"):
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

            # 4) Ganha por emoÃ§Ã£o atual (com intensidade fisiolÃ³gica)
            # --- usa Ãºltima percepÃ§Ã£o disponÃ­vel para evitar loop fisiolÃ³gico ---
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
            if emocao in ("alegria", "serenidade", "amor", "gratidÃ£o"):
                afetos[autor_atual]["confianca"] += 0.7 * ganho
                afetos[autor_atual]["gratidao"]  += 0.5 * ganho
            elif emocao in ("medo", "ansiedade", "inseguranÃ§a"):
                afetos[autor_atual]["ansiedade"] += 0.6 * ganho
                afetos[autor_atual]["confianca"] -= 0.3 * ganho
            elif emocao in ("tristeza", "saudade"):
                afetos[autor_atual]["saudade"]   += 0.5 * ganho
            elif emocao in ("raiva", "irritacao", "irritaÃ§Ã£o"):
                afetos[autor_atual]["ansiedade"] += 0.4 * ganho
                afetos[autor_atual]["confianca"] -= 0.4 * ganho

            # Clamp 0..1
            for k in ("confianca", "gratidao", "saudade", "ansiedade"):
                afetos[autor_atual][k] = float(max(0.0, min(1.0, afetos[autor_atual][k])))

            afetos[autor_atual]["_last"] = now.isoformat()

            # 5) Persiste
            with open(afetos_path, "w", encoding="utf-8") as f:
                json.dump(afetos, f, ensure_ascii=False, indent=2)
        except Exception:
            # NÃ£o deixa afetar o fluxo conversacional
            pass

    
    def _registrar_interocepcao(self, emocao_rotulada):
        """
        Recoleta percepÃ§Ã£o atual e registra trace emocional + interoceptivo
        com seguranÃ§a de chaves.
        """
        try:
            percepcao = self.perceber()  # pega sensaÃ§Ãµes, intensidade e deltas pÃ³s-ajuste
            sensacoes = percepcao.get("sensacoes", [])
            intensidade = percepcao.get("intensidade", 0.0)
            deltas = percepcao.get("deltas", {})
        except Exception:
            sensacoes, intensidade, deltas = [], 0.0, {}

        # Quem provocou a emoÃ§Ã£o (Ãºltimo autor no memory)
        autor_atual = "desconhecido"
        try:
            import json
            with open("angela_memory.jsonl", "r", encoding="utf-8") as f:
                linhas = [json.loads(l) for l in f if l.strip()]
            if linhas:
                ult = linhas[-1]
                # aceita o formato novo (dict) ou o antigo (string)
                if isinstance(ult.get("user"), dict):
                    autor_atual = ult["user"].get("autor", "desconhecido")
                else:
                    autor_atual = "Vinicius"
        except Exception:
            pass

        # === ValidaÃ§Ã£o: prevenir auto-referÃªncia ===
        # Angela nÃ£o processa vÃ­nculos de eventos auto-gerados
        if str(autor_atual).lower() in ("sistema", "sistema(deepawake)", "angela", "Ã¢ngela", "desconhecido"):
            return

        # grava trace emocional
        try:
            import json, datetime
            with open("angela_emotional_trace.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "emocao": emocao_rotulada,
                    "causado_por": autor_atual
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # grava snapshot interoceptivo
        try:
            import json, datetime
            with open("angela_interoception.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "sensacoes": sensacoes,
                    "intensidade": intensidade,
                    "deltas": deltas
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def regular_emocao(self, modo: str):
        """
        CORRIGIDO: MÃ©todo de instÃ¢ncia (nÃ£o funÃ§Ã£o global)
        
        modo: 'inseguranca' | 'medo_leve' | 'alivio' | 'dopamina'
        Ajusta variÃ¡veis fisiolÃ³gicas do corpo digital de forma sutil.
        """
        if not hasattr(self.corpo, "ajustar"):
            # fallback: tenta mexer nos atributos bÃ¡sicos se existirem
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
