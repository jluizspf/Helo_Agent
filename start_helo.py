import requests
import json
import os
from datetime import datetime

# --- CONFIGURAÇÕES DA CASA DE MÁQUINAS ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO = "llama3"  # Substitua caso o nome do seu modelo no Ollama seja diferente
DIARIO_PATH = "/mnt/Paiol/4_Projetos_Python/Helo_Agent/DiarioDeBordo.txt"

# Memória de curto prazo da sessão atual
historico_sessao = []


# ==========================================
# MÓDULO 1: INICIALIZAÇÃO (Leitura do Diário)
# ==========================================
def ler_ultima_sessao():
    """Lê o Diário de Bordo e extrai apenas o resumo da última sessão."""
    if not os.path.exists(DIARIO_PATH):
        return "Nenhum registro anterior encontrado. Esta é a primeira sessão."

    try:
        with open(DIARIO_PATH, "r", encoding="utf-8") as arquivo:
            conteudo = arquivo.read()

        # O Python fatia o texto do arquivo usando a nossa flag de marcação
        sessoes = conteudo.split("--- SESSÃO ")
        if len(sessoes) > 1:
            ultima_sessao = sessoes[-1].strip()  # Pega apenas o último bloco
            return f"Último registro gravado:\n{ultima_sessao}"
        else:
            return "Nenhum registro válido encontrado."
    except Exception as e:
        return f"[Erro de Leitura]: {e}"


# ==========================================
# MÓDULO 2: RAG LOCAL (Busca sob demanda)
# ==========================================
def buscar_no_diario(termo_busca):
    """Varre o Diário de Bordo procurando o termo e retorna o bloco de texto."""
    if not os.path.exists(DIARIO_PATH):
        return "O Diário de Bordo ainda não existe no Paiol."

    try:
        with open(DIARIO_PATH, "r", encoding="utf-8") as arquivo:
            conteudo = arquivo.read()

        # Fatia o arquivo usando o nosso delimitador de data
        sessoes = conteudo.split("--- SESSÃO ")
        resultados = []

        # Itera sobre os blocos procurando a palavra exata
        for sessao in sessoes:
            if termo_busca.lower() in sessao.lower() and sessao.strip() != "":
                resultados.append(f"SESSÃO {sessao.strip()}")

        if resultados:
            # Junta todos os blocos onde a palavra apareceu
            return "\n\n".join(resultados)
        else:
            return f"Nenhum registro encontrado sobre '{termo_busca}'."
    except Exception as e:
        return f"[Erro de Leitura do Arquivo]: {e}"


# ==========================================
# MÓDULO 3: ENCERRAMENTO (Sumarização)
# ==========================================
def resumir_e_salvar(historico):
    """Pede para a Helo resumir a sessão atual e salva no .txt."""
    print("\n[Sistema] Acionando rotina de desligamento... Solicitando síntese de dados à Helo.")

    # Criamos um "pedido fantasma" no histórico só para forçar ela a resumir
    prompt_resumo = historico + [{
        "role": "user",
        "content": "Faça um resumo de no máximo 3 linhas da nossa conversa de hoje, focando estritamente nos tópicos técnicos e no problema que resolvemos. Não faça saudações, apenas entregue o resumo técnico para o log do sistema."
    }]

    payload = {
        "model": MODELO,
        "messages": prompt_resumo,
        "stream": False
    }

    try:
        # Pede o resumo para a API do Ollama
        resposta = requests.post(OLLAMA_URL, json=payload)
        resposta.raise_for_status()
        resumo = resposta.json()["message"]["content"]

        # Grava fisicamente no disco do Dreadnought
        with open(DIARIO_PATH, "a", encoding="utf-8") as arquivo:
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            arquivo.write(f"\n\n--- SESSÃO {data_atual} ---\n")
            arquivo.write(resumo)

        print("[Sistema] Síntese concluída. Diário de Bordo gravado com sucesso no Paiol!")

    except Exception as e:
        print(f"\n[Erro Crítico] Falha ao gerar a síntese ou gravar no disco: {e}")

# ==========================================
# MOTOR PRINCIPAL (Loop de Comunicação)
# ==========================================
def main():
    print("Iniciando Sistema de Imediato (Helo)...\n")

    # 1. Prepara o contexto inicial com o passado
    contexto_anterior = ler_ultima_sessao()

    # 2. Injeta o System Prompt oculto com as regras de alucinação e o contexto
    mensagem_sistema = {
        "role": "system",
        "content": f"""Você é a Helo, a Imediato do servidor Dreadnought.
        DIRETIVAS RIGOROSAS:
        DIRETIVAS RIGOROSAS:
        - Se o usuário solicitar informações que constam no contexto injetado (registros históricos), utilize essas informações para responder com precisão.
        - Você não tem memória de sessões passadas FORA do que é injetado pelo sistema. Se uma informação NÃO estiver no contexto injetado, aí sim, você deve confessar que não possui o registro.
        - Não alucine ações de sistema.

        RESUMO DA ÚLTIMA SESSÃO (Use como ponto de partida):
        {contexto_anterior}
        """
    }
    historico_sessao.append(mensagem_sistema)

    print("Helo online. Digite '/sair' para encerrar ou '/lembrar [termo]' para buscar nos registros.\n")

    # Loop contínuo de chat
    while True:
        entrada_usuario = input("Comandante: ")

        # Interceptadores de Comando
        if entrada_usuario.strip() == "/sair":
            resumir_e_salvar(historico_sessao)
            print("Helo desativada. Bom descanso, comandante.")
            break

        elif entrada_usuario.startswith("/lembrar"):
            termo = entrada_usuario.replace("/lembrar", "").strip()

            if not termo:
                print("[Sistema] Digite um termo após o comando. Exemplo: /lembrar Python")
                continue

            print(f"\n[Dreadnought Buscando nos Arquivos por '{termo}'...]")
            resultado_busca = buscar_no_diario(termo)

            print(f"Resultado:\n{resultado_busca}\n")

            # Injeta silenciosamente no contexto para que a Helo passe a "saber" da informação
            historico_sessao.append({
                "role": "system",
                "content": f"O usuário pesquisou nos arquivos do sistema por '{termo}'. Os registros encontrados foram:\n{resultado_busca}\nUse essa informação caso o usuário faça perguntas agora."
            })
            continue  # Pula o envio direto para a IA e aguarda você conversar com ela

        # Adiciona a fala do usuário ao histórico da sessão
        historico_sessao.append({"role": "user", "content": entrada_usuario})

        # AQUI ENTRARÁ A LÓGICA DE CHAMADA DA API DO OLLAMA
        # Monta o pacote de dados (Payload) no padrão que a API do Ollama exige
        payload = {
            "model": MODELO,
            "messages": historico_sessao,
            "stream": False  # Mantemos em False por enquanto para estabilidade dos dados
        }

        try:
            # Dispara a requisição HTTP POST para o servidor do Ollama local
            resposta = requests.post(OLLAMA_URL, json=payload)
            resposta.raise_for_status()  # Verifica se a API não retornou nenhum erro

            # Desempacota o JSON recebido e extrai apenas a fala da Helo
            dados = resposta.json()
            fala_helo = dados["message"]["content"]

            print(f"\nHelo: {fala_helo}\n")

            # Grava a resposta da Helo na memória de curto prazo para manter o contexto
            historico_sessao.append({"role": "assistant", "content": fala_helo})

        except requests.exceptions.RequestException as e:
            print(
                f"\n[Erro Crítico]: Falha na comunicação com o motor de inferência. O Ollama está rodando? Detalhes: {e}\n")

if __name__ == "__main__":
    main()