import requests
import json
import os
import psutil # NOVO IMPORT
from datetime import datetime

# --- CONFIGURAÇÕES DA CASA DE MÁQUINAS ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO = "llama3"  # Substitua caso o nome do seu modelo no Ollama seja diferente
DIARIO_PATH = "/mnt/Paiol/4_Projetos_Python/LembrançaDeHelo/DiarioDeBordo.txt"
TAREFAS_PATH = "/mnt/Paiol/4_Projetos_Python/LembrançaDeHelo/Tarefas.txt" # NOVA LINHA

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
# MÓDULO 4: GESTÃO DE TAREFAS (To-Do List)
# ==========================================
def ler_tarefas():
    """Lê o arquivo de tarefas e retorna uma lista numerada."""
    if not os.path.exists(TAREFAS_PATH):
        return "Nenhuma tarefa pendente no momento."

    try:
        with open(TAREFAS_PATH, "r", encoding="utf-8") as arquivo:
            linhas = arquivo.readlines()

        if not linhas:
            return "Nenhuma tarefa pendente no momento."

        # Formata as linhas em uma lista numerada (Ex: 1. Estudar Python)
        lista_formatada = ""
        for i, linha in enumerate(linhas):
            lista_formatada += f"{i + 1}. {linha.strip()}\n"
        return lista_formatada.strip()
    except Exception as e:
        return f"[Erro de Leitura]: {e}"


def adicionar_tarefa(descricao):
    """Adiciona uma nova linha ao final do arquivo de tarefas."""
    try:
        with open(TAREFAS_PATH, "a", encoding="utf-8") as arquivo:
            arquivo.write(descricao + "\n")
        return f"Tarefa adicionada: '{descricao}'"
    except Exception as e:
        return f"[Erro de Gravação]: {e}"


def concluir_tarefa(numero_tarefa):
    """Remove a tarefa da lista com base no número digitado."""
    if not os.path.exists(TAREFAS_PATH):
        return "Arquivo de tarefas não encontrado."

    try:
        with open(TAREFAS_PATH, "r", encoding="utf-8") as arquivo:
            linhas = arquivo.readlines()

        if 0 < numero_tarefa <= len(linhas):
            tarefa_removida = linhas.pop(numero_tarefa - 1).strip()

            # Sobrescreve o arquivo com a lista atualizada
            with open(TAREFAS_PATH, "w", encoding="utf-8") as arquivo:
                arquivo.writelines(linhas)
            return f"Tarefa concluída e removida: '{tarefa_removida}'"
        else:
            return f"Tarefa número {numero_tarefa} não encontrada."
    except Exception as e:
        return f"[Erro na Remoção]: {e}"

# ==========================================
# MÓDULO 5: TELEMETRIA DO SISTEMA
# ==========================================
def ler_sensores_sistema():
    """Coleta dados reais de CPU e RAM do hardware hospedeiro."""
    try:
        # interval=1 faz o script pausar por 1 seg para calcular a média de uso real da CPU
        uso_cpu = psutil.cpu_percent(interval=1)

        # Extrai os dados da RAM (vêm em bytes, convertemos para GB)
        memoria = psutil.virtual_memory()
        uso_ram_percent = memoria.percent
        ram_total_gb = memoria.total / (1024 ** 3)
        ram_usada_gb = memoria.used / (1024 ** 3)

        relatorio = (
            f"- Uso de CPU: {uso_cpu}%\n"
            f"- Uso de RAM: {uso_ram_percent}% ({ram_usada_gb:.2f} GB de {ram_total_gb:.2f} GB)"
        )
        return relatorio
    except Exception as e:
        return f"[Erro na Leitura dos Sensores]: {e}"

# ==========================================
# MOTOR PRINCIPAL (Loop de Comunicação)
# ==========================================
def main():
    print("Iniciando Sistema de Imediato (Helo)...\n")

    # 1. Prepara o contexto inicial com o passado e as tarefas pendentes
    contexto_anterior = ler_ultima_sessao()
    tarefas_pendentes = ler_tarefas()

    # 2. Injeta o System Prompt oculto com as regras de alucinação e o contexto
    mensagem_sistema = {
        "role": "system",
        "content": f"""Você é a Helo, a Imediato do servidor Dreadnought.
            DIRETIVAS RIGOROSAS:
            - Utilize o contexto injetado (histórico e tarefas) para responder ao usuário.
            - Não alucine ações de sistema (como criar ou mover arquivos).

            TAREFAS PENDENTES DO COMANDANTE:
            {tarefas_pendentes}

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

        elif entrada_usuario.startswith("/tarefa add"):
            nova_tarefa = entrada_usuario.replace("/tarefa add", "").strip()
            if nova_tarefa:
                resultado = adicionar_tarefa(nova_tarefa)
                print(f"[Sistema]: {resultado}")
            else:
                print("[Sistema]: Digite a tarefa. Ex: /tarefa add Estudar pandas")
            continue

        elif entrada_usuario.strip() == "/tarefa listar":
            print(f"\n[Tarefas Pendentes]:\n{ler_tarefas()}\n")
            continue

        elif entrada_usuario.startswith("/tarefa concluir"):
            try:
                # Extrai o número que o usuário digitou
                num = int(entrada_usuario.replace("/tarefa concluir", "").strip())
                resultado = concluir_tarefa(num)
                print(f"[Sistema]: {resultado}")
            except ValueError:
                print("[Sistema]: Digite o número da tarefa. Ex: /tarefa concluir 1")
            continue

        elif entrada_usuario.strip() == "/status":
            print("\n[Sistema] Lendo sensores do núcleo do Dreadnought. Aguarde 1 segundo...")
            dados_sensores = ler_sensores_sistema()

            # Substituímos o "/status" por um prompt formatado com os dados reais
            entrada_usuario = (
                f"Comandante solicita relatório de status. "
                f"Analise os seguintes dados reais do servidor agora e responda de forma técnica e imersiva como a Imediato do Dreadnought:\n{dados_sensores}"
            )
            # Não usamos 'continue' aqui!
            # Deixamos o fluxo descer. O Python vai adicionar essa frase ao histórico e chamar a API normalmente.

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