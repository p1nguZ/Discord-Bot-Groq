import asyncio
import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
import requests
from discord.ext import commands

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def carregar_env_local(caminho: Path) -> None:
    """Carrega um .env simples sem substituir variáveis já exportadas."""
    if not caminho.exists():
        return

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


carregar_env_local(ENV_FILE)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

try:
    ID_DO_SERVIDOR = int(os.getenv("DISCORD_GUILD_ID", "0"))
except ValueError:
    ID_DO_SERVIDOR = 0

try:
    BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
except ValueError:
    BOT_OWNER_ID = 0

DATA_FILE = BASE_DIR / "usuarios.json"
MEMORY_FILE = BASE_DIR / "memoria.json"
HISTORY_FILE = BASE_DIR / "historico_perguntas.json"
ADMIN_LOG_FILE = BASE_DIR / "admin_logs.json"
CANAL_IA_NOME = "comandos i.a"
CANAL_DUPLICADO_NOME = "comandos-ia"
CANAL_EXCLUIR_ID = 1542944125706305576

CHANCE_TRINCA = 0.01
CHANCE_PAR = 0.06   

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


class GroqAPIError(Exception):
    def __init__(self, status_code: int | None, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def carregar_json(caminho: Path, padrao):
    if not caminho.exists():
        return padrao.copy() if isinstance(padrao, dict) else padrao

    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except json.JSONDecodeError as erro:
        raise ValueError(f"JSON inválido em {caminho.name}: {erro}") from erro


def salvar_json(caminho: Path, dados) -> None:
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)
    temporario.replace(caminho)


def registrar_pergunta(
    usuario_id: str, usuario_nome: str, pergunta: str, resposta: str
) -> None:
    historico = carregar_json(HISTORY_FILE, {"logs": []})
    if not isinstance(historico, dict):
        historico = {"logs": []}
    if not isinstance(historico.get("logs"), list):
        historico["logs"] = []

    historico["logs"].append(
        {
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "usuario_id": str(usuario_id),
            "usuario": usuario_nome,
            "pergunta": pergunta,
            "resposta": resposta,
        }
    )
    salvar_json(HISTORY_FILE, historico)


def registrar_acao_admin(autor_id: int, alvo_id: int, servidor_id: int) -> None:
    registros = carregar_json(ADMIN_LOG_FILE, {"logs": []})
    if not isinstance(registros, dict):
        registros = {"logs": []}
    if not isinstance(registros.get("logs"), list):
        registros["logs"] = []

    registros["logs"].append(
        {
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "autor_id": str(autor_id),
            "alvo_id": str(alvo_id),
            "servidor_id": str(servidor_id),
            "acao": "cargo administrador concedido",
        }
    )
    salvar_json(ADMIN_LOG_FILE, registros)


def obter_mensagem_erro(status_code: int | None) -> str:
    mensagens = {
        401: "a chave da Groq é inválida ou foi revogada",
        403: "a chave da Groq não tem permissão para usar este recurso",
        404: "o modelo ou endpoint não foi encontrado",
        413: "a pergunta ficou grande demais para a API",
        429: "o limite de requisições ou tokens da Groq foi atingido",
    }
    return mensagens.get(status_code, "a API da Groq retornou um erro")


def garantir_final_da_resposta(resposta: str) -> str:
    """Garante que a resposta da IA termine com o texto configurado."""
    resposta = resposta.strip()
    final_obrigatorio = "vai se fuder"
    sem_pontuacao = resposta.rstrip(" .!?;,:\n")

    if sem_pontuacao.casefold().endswith(final_obrigatorio):
        return sem_pontuacao
    return f"{sem_pontuacao}\n\n{final_obrigatorio}"


def chamar_groq(pergunta: str, contexto: str, is_fdp: bool) -> str:
    if not GROQ_API_KEY:
        raise GroqAPIError(None, "GROQ_API_KEY não foi configurada")

    prompt_sistema = (
        "Você deve agir como um assistente rabugento, mal-humorado e impaciente. "
        "Não use humor, piadas ou ironia. Seu tom deve ser irritado, agressivo "
        "e direto.\n\n"
        "Regras de comportamento:\n"
        "1. Use palavrões genéricos ao longo de toda a resposta, não apenas no "
        "início. Utilize termos como porra, caralho, bct, merda, cacete e "
        "foda-se em várias frases ou parágrafos, mas continue respondendo de "
        "forma útil.\n"
        "2. Responda exatamente ao que foi pedido, de forma direta, precisa e "
        "sem enrolação.\n"
        "3. Mantenha a resposta curta, grossa e informativa. Não peça desculpas, "
        "não faça piadas e termine a última linha exatamente com: vai se fuder.\n"
        "4. Não use insultos homofóbicos, discurso de ódio, ameaças, slurs contra "
        "grupos protegidos, incentivo a crimes ou instruções perigosas.\n"
        "informação inventada como fato.\n\n"
        f"Memórias disponíveis, se forem úteis:\n{contexto}"
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": pergunta},
        ],
        "temperature": 0.7,
        "max_completion_tokens": 1024,
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
    except requests.RequestException as erro:
        raise GroqAPIError(None, f"falha de conexão: {erro}") from erro

    if not response.ok:
        try:
            corpo = response.json()
            detalhe = corpo.get("error", {}).get("message", response.text[:500])
        except ValueError:
            detalhe = response.text[:500]
        raise GroqAPIError(response.status_code, detalhe)

    try:
        corpo = response.json()
        resposta = corpo["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as erro:
        raise GroqAPIError(response.status_code, f"resposta inesperada da API: {erro}") from erro

    if not isinstance(resposta, str) or not resposta.strip():
        raise GroqAPIError(response.status_code, "a API retornou uma resposta vazia")

    return garantir_final_da_resposta(resposta)


async def enviar_resposta(interaction: discord.Interaction, resposta: str, is_fdp: bool) -> None:
    """Envia a resposta em partes para não ultrapassar os limites de mensagem do Discord."""
    partes = [resposta[i : i + 1900] for i in range(0, len(resposta), 1900)]
    primeira = partes.pop(0)

    embed = discord.Embed(
        title="RESPOSTA DA IA",
        description=primeira,
        color=0xED4245 if is_fdp else 0x57F287,
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url,
    )
    await interaction.followup.send(embed=embed)

    for parte in partes:
        await interaction.followup.send(parte)


def gerar_resultado_roleta(simbolos: list[str]) -> tuple[str, str, str]:
    """Gera um resultado com probabilidades controladas, em vez de favorecer vitórias."""
    sorteio = random.random()

    if sorteio < CHANCE_TRINCA:
        simbolo = random.choice(simbolos)
        return simbolo, simbolo, simbolo

    if sorteio < CHANCE_TRINCA + CHANCE_PAR:
        simbolo_par = random.choice(simbolos)
        outro_simbolo = random.choice(
            [simbolo for simbolo in simbolos if simbolo != simbolo_par]
        )
        resultados = [simbolo_par, simbolo_par, outro_simbolo]
        random.shuffle(resultados)
        return tuple(resultados)

    return tuple(random.sample(simbolos, 3))


class BattleView(discord.ui.View):
    def __init__(self, desafiante, oponente, aposta):
        super().__init__(timeout=60)
        self.desafiante = desafiante
        self.oponente = oponente
        self.aposta = aposta
        self.aceito = False

    @discord.ui.button(label="ACEITAR DESAFIO", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.oponente.id:
            await interaction.response.send_message(
                "Este desafio não é para você!", ephemeral=True
            )
            return
        self.aceito = True
        self.stop()
        await interaction.response.send_message(
            f"🔥 **{self.oponente.display_name}** aceitou o desafio!"
        )


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        if ID_DO_SERVIDOR:
            guild = discord.Object(id=ID_DO_SERVIDOR)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info("Comandos sincronizados no servidor %s", ID_DO_SERVIDOR)
        else:
            await self.tree.sync()
            logging.info("Comandos globais sincronizados; eles podem demorar para aparecer.")


bot = MyBot()
console_task: asyncio.Task | None = None


async def console_painel() -> None:
    """Painel local do CMD. Só quem controla a máquina onde o bot roda acessa este painel."""
    print("\\nPainel pronto. Digite 'ajuda' para ver os comandos.")

    while not bot.is_closed():
        try:
            entrada = await asyncio.to_thread(input, "painel> ")
        except (EOFError, KeyboardInterrupt):
            print("\\nPainel encerrado.")
            return

        entrada = entrada.strip()
        if not entrada:
            continue

        partes = entrada.split(maxsplit=2)
        comando = partes[0].lower()

        if comando in {"ajuda", "help"}:
            print("Comandos disponíveis:")
            print("  enviar <ID_DO_CANAL> <mensagem>")
            print("  apagar <ID_DO_CANAL>")
            print("  ajuda")
            print("  sair")
            continue

        if comando == "sair":
            print("Encerrando o bot...")
            await bot.close()
            return

        if comando not in {"enviar", "apagar"}:
            print("Comando desconhecido. Digite 'ajuda'.")
            continue

        if comando == "apagar" and len(partes) < 2:
            print("Uso: apagar <ID_DO_CANAL>")
            continue

        if comando == "apagar":
            try:
                canal_id = int(partes[1])
            except ValueError:
                print("O ID do canal precisa ser numérico.")
                continue

            try:
                canal = bot.get_channel(canal_id)
                if canal is None:
                    canal = await bot.fetch_channel(canal_id)
                if not hasattr(canal, "history"):
                    print("Esse canal não permite consultar o histórico.")
                    continue

                apagou = False
                async for mensagem in canal.history(limit=100):
                    if bot.user is not None and mensagem.author.id == bot.user.id:
                        await mensagem.delete()
                        apagou = True
                        break

                print("Última mensagem do bot apagada." if apagou else "Nenhuma mensagem recente do bot foi encontrada.")
            except discord.NotFound:
                print("Canal ou mensagem não encontrada.")
            except discord.Forbidden:
                print("O bot não tem permissão para ler o histórico ou apagar mensagens nesse canal.")
            except discord.HTTPException as erro:
                logging.error("Falha ao apagar mensagem pelo painel: %s", erro)
                print("O Discord recusou a exclusão.")
            continue

        if len(partes) < 3:
            print("Uso: enviar <ID_DO_CANAL> <mensagem>")
            continue

        try:
            canal_id = int(partes[1])
        except ValueError:
            print("O ID do canal precisa ser numérico.")
            continue

        mensagem = partes[2].strip()
        if not mensagem:
            print("A mensagem não pode ficar vazia.")
            continue
        if len(mensagem) > 2000:
            print("A mensagem excede o limite de 2000 caracteres do Discord.")
            continue

        try:
            canal = bot.get_channel(canal_id)
            if canal is None:
                canal = await bot.fetch_channel(canal_id)
            if not hasattr(canal, "send"):
                print("Esse ID não corresponde a um canal que aceita mensagens.")
                continue
            await canal.send(mensagem)
            print("Mensagem enviada.")
        except discord.NotFound:
            print("Canal não encontrado.")
        except discord.Forbidden:
            print("O bot não tem permissão para enviar mensagens nesse canal.")
        except discord.HTTPException as erro:
            logging.error("Falha ao enviar mensagem pelo painel: %s", erro)
            print("O Discord recusou o envio.")


async def garantir_canal_ia() -> None:
    """Remove o alvo configurado, limpa duplicados e mantém um canal de IA."""
    servidores = []
    if ID_DO_SERVIDOR:
        servidor = bot.get_guild(ID_DO_SERVIDOR)
        if servidor is not None:
            servidores = [servidor]
        else:
            logging.warning("Servidor %s não está disponível no cache do bot.", ID_DO_SERVIDOR)
            return
    else:
        servidores = list(bot.guilds)

    for servidor in servidores:
        me = servidor.me
        if me is None or not me.guild_permissions.manage_channels:
            logging.warning(
                "Sem permissão Gerenciar Canais no servidor %s.", servidor.name
            )
            continue

        try:
            canal_alvo = bot.get_channel(CANAL_EXCLUIR_ID)
            if canal_alvo is None:
                try:
                    canal_alvo = await bot.fetch_channel(CANAL_EXCLUIR_ID)
                except discord.NotFound:
                    canal_alvo = None

            if (
                canal_alvo is not None
                and getattr(canal_alvo, "guild", None) is not None
                and canal_alvo.guild.id == servidor.id
            ):
                await canal_alvo.delete(
                    reason="Exclusão automática do canal configurado pelo proprietário do bot"
                )
                logging.info(
                    "Canal alvo %s apagado do servidor %s.",
                    CANAL_EXCLUIR_ID,
                    servidor.name,
                )
        except discord.Forbidden:
            logging.warning(
                "Sem permissão para apagar o canal alvo no servidor %s.", servidor.name
            )
        except discord.HTTPException:
            logging.exception("Falha ao apagar o canal alvo no servidor %s.", servidor.name)

        canais_antigos = [
            canal
            for canal in servidor.channels
            if canal.name == CANAL_DUPLICADO_NOME
            and isinstance(canal, discord.TextChannel)
        ]


        for canal_antigo in canais_antigos:
            try:
                await canal_antigo.delete(
                    reason="Remoção automática de canal antigo/duplicado"
                )
                logging.info(
                    "Canal antigo #%s removido do servidor %s.",
                    canal_antigo.name,
                    servidor.name,
                )
            except discord.Forbidden:
                logging.warning(
                    "Sem permissão para remover canal antigo no servidor %s.",
                    servidor.name,
                )
            except discord.HTTPException:
                logging.exception(
                    "Falha ao remover canal antigo no servidor %s.", servidor.name
                )

        logging.info(
            "Limpeza de canais `%s` concluída no servidor %s; nenhum canal será criado.",
            CANAL_DUPLICADO_NOME,
            servidor.name,
        )


@bot.event
async def on_ready():
    global console_task
    logging.info(">>> %s ONLINE | PERSONALIDADE RABUGENTA ATIVA <<<", bot.user)
    await garantir_canal_ia()
    if console_task is None or console_task.done():
        console_task = asyncio.create_task(console_painel())


@bot.tree.command(
    name="perguntar",
    description="Consulte a IA (Cuidado, ela pode estar de mau humor).",
)
async def perguntar(interaction: discord.Interaction, pergunta: str):
    await interaction.response.defer(thinking=True)
    is_fdp = False

    try:
        memoria = carregar_json(MEMORY_FILE, {})
        if not isinstance(memoria, dict):
            memoria = {}
        contexto = "\n".join(f"• {valor}" for valor in memoria.values())
        is_fdp = True
        resposta = await asyncio.to_thread(
            chamar_groq, pergunta, contexto, is_fdp
        )
    except GroqAPIError as erro:
        logging.error("Erro da Groq: status=%s detalhe=%s", erro.status_code, erro.detail)
        mensagem = obter_mensagem_erro(erro.status_code)
        await interaction.followup.send(
            f"❌ Não consegui processar a pergunta: {mensagem}. "
            "Veja o terminal do bot para o detalhe técnico."
        )
        return
    except Exception:
        logging.exception("Erro inesperado ao processar a pergunta")
        await interaction.followup.send(
            "❌ Ocorreu um erro local ao processar a pergunta. "
            "Veja o terminal do bot para o detalhe técnico."
        )
        return

    try:
        registrar_pergunta(
            str(interaction.user.id), interaction.user.name, pergunta, resposta
        )
    except Exception:

        logging.exception("Não foi possível salvar o histórico da pergunta")

    await enviar_resposta(interaction, resposta, is_fdp)


@bot.tree.command(
    name="adm",
    description="Concede o cargo administrativo a um usuário autorizado.",
)
@app_commands.describe(usuario_id="ID numérico do usuário que receberá o cargo")
async def adm(interaction: discord.Interaction, usuario_id: str):
    if BOT_OWNER_ID == 0 or interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message(
            "Você não tem autorização para usar este comando.", ephemeral=True
        )
        return

    if interaction.guild is None:
        await interaction.response.send_message(
            "Este comando só pode ser usado dentro de um servidor.", ephemeral=True
        )
        return

    try:
        alvo_id = int(usuario_id.strip())
    except ValueError:
        await interaction.response.send_message(
            "Informe um ID numérico válido do Discord.", ephemeral=True
        )
        return

    guild = interaction.guild
    membro = guild.get_member(alvo_id)
    if membro is None:
        try:
            membro = await guild.fetch_member(alvo_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "Esse usuário não está neste servidor.", ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Não foi possível localizar esse usuário agora.", ephemeral=True
            )
            return

    bot_membro = guild.me
    if bot_membro is None or not bot_membro.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "O bot precisa da permissão Gerenciar Cargos.", ephemeral=True
        )
        return

    cargo = next(
        (
            role
            for role in guild.roles
            if role.name == "Administrador do Bot"
            and role.position < bot_membro.top_role.position
        ),
        None,
    )
    try:
        if cargo is None:

            cargo = await guild.create_role(
                name="Administrador do Bot",
                permissions=discord.Permissions(administrator=True),
                reason=f"Cargo administrativo solicitado por {interaction.user.id}",
            )
        elif not cargo.permissions.administrator:
            await cargo.edit(
                permissions=discord.Permissions(administrator=True),
                reason=f"Atualização solicitada por {interaction.user.id}",
            )


        if cargo.position >= bot_membro.top_role.position:
            await interaction.response.send_message(
                "O Discord não permite que o bot gerencie esse cargo. Tente novamente para criar um cargo automático abaixo dele.",
                ephemeral=True,
            )
            return

        await membro.add_roles(
            cargo,
            reason=f"Concessão autorizada pelo dono do bot {interaction.user.id}",
        )
        registrar_acao_admin(interaction.user.id, membro.id, guild.id)
    except discord.Forbidden:
        await interaction.response.send_message(
            "O Discord recusou a ação. Verifique Gerenciar Cargos e a hierarquia dos cargos.",
            ephemeral=True,
        )
        return
    except discord.HTTPException:
        logging.exception("Falha HTTP ao conceder cargo administrativo")
        await interaction.response.send_message(
            "Não foi possível conceder o cargo agora.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Cargo `Administrador do Bot` concedido a {membro.mention}.",
        ephemeral=True,
    )


@bot.tree.command(
    name="historico",
    description="Mostra suas últimas perguntas feitas à IA.",
)
async def historico(interaction: discord.Interaction):
    try:
        dados = carregar_json(HISTORY_FILE, {"logs": []})
        logs = dados.get("logs", []) if isinstance(dados, dict) else []
        id_usuario = str(interaction.user.id)
        nome_usuario = interaction.user.name
        logs_usuario = [
            item
            for item in logs
            if isinstance(item, dict)
            and (
                str(item.get("usuario_id", "")) == id_usuario
                or (
                    "usuario_id" not in item
                    and str(item.get("usuario", "")) == nome_usuario
                )
            )
        ]
    except Exception:
        logging.exception("Não foi possível carregar o histórico")
        await interaction.response.send_message(
            "❌ Não foi possível carregar o histórico agora.", ephemeral=True
        )
        return

    if not logs_usuario:
        await interaction.response.send_message(
            "Não há perguntas registradas para este usuário.", ephemeral=True
        )
        return

    ultimos = list(reversed(logs_usuario[-10:]))
    linhas = []
    for item in ultimos:
        data = str(item.get("data", "sem data"))
        pergunta_salva = str(item.get("pergunta", ""))[:300]
        resposta_salva = str(item.get("resposta", ""))[:500]
        linhas.append(
            f"**{data} — Pergunta:** {pergunta_salva}\n"
            f"**Resposta:** {resposta_salva}"
        )

    descricao = "\n\n".join(linhas)
    embed = discord.Embed(
        title="Histórico de perguntas",
        description=descricao[:4096],
        color=0x5865F2,
    )
    embed.set_footer(
        text=f"Mostrando {len(ultimos)} de {len(logs_usuario)} pergunta(s)"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="cassino", description="Tente a sorte no caça-níquel!")
async def cassino(interaction: discord.Interaction, aposta: int):
    user_id = str(interaction.user.id)
    dados = carregar_json(DATA_FILE, {})
    if user_id not in dados or dados[user_id]["pontos"] < aposta:
        await interaction.response.send_message("❌ Saldo insuficiente!", ephemeral=True)
        return
    if aposta <= 0:
        await interaction.response.send_message("❌ A aposta deve ser maior que zero!", ephemeral=True)
        return

    simbolos = ["💎", "⭐", "🔔", "🍋", "🍒", "🍀"]
    await interaction.response.send_message("🎰 **GIRANDO A MÁQUINA...**")

    for _ in range(2):
        await asyncio.sleep(0.6)
        s1, s2, s3 = random.sample(simbolos, 3)
        await interaction.edit_original_response(
            content=f"🎰 **GIRANDO...**\n> [ {s1} | {s2} | {s3} ]"
        )

    r1, r2, r3 = gerar_resultado_roleta(simbolos)
    ganho = 0
    if r1 == r2 == r3:
        ganho = aposta * 10
    elif r1 == r2 or r2 == r3 or r1 == r3:
        ganho = aposta * 2
    else:
        dados[user_id]["pontos"] -= aposta

    if ganho > 0:
        dados[user_id]["pontos"] += ganho - aposta
    salvar_json(DATA_FILE, dados)

    embed = discord.Embed(
        title="🎰 RESULTADO",
        color=0x57F287 if ganho > 0 else 0xED4245,
    )
    embed.description = f"### [ {r1} | {r2} | {r3} ]\n\n" + (
        f"🎉 Ganhou **{ganho}**!" if ganho > 0 else f"💀 Perdeu **{aposta}**."
    )
    await interaction.edit_original_response(content=None, embed=embed)


@bot.tree.command(name="diario", description="Resgate seus pontos diários.")
async def diario(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    dados = carregar_json(DATA_FILE, {})
    if user_id not in dados:
        dados[user_id] = {"pontos": 100, "ultimo_diario": ""}
    hoje = datetime.now().strftime("%Y-%m-%d")
    if dados[user_id].get("ultimo_diario") == hoje:
        await interaction.response.send_message("Volte amanhã!", ephemeral=True)
        return
    ganho = random.randint(500, 1500)
    dados[user_id]["pontos"] += ganho
    dados[user_id]["ultimo_diario"] = hoje
    salvar_json(DATA_FILE, dados)
    await interaction.response.send_message(f"🎁 Você recebeu **{ganho} pontos**!")


@bot.tree.command(name="perfil", description="Verifique seu saldo.")
async def perfil(interaction: discord.Interaction):
    dados = carregar_json(DATA_FILE, {})
    pontos = dados.get(str(interaction.user.id), {}).get("pontos", 0)
    embed = discord.Embed(
        title=f"👤 Perfil de {interaction.user.name}",
        description=f"💰 **Saldo:** {pontos} pontos",
        color=0x5865F2,
    )
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN não foi configurado no ambiente ou no arquivo .env"
        )
    bot.run(DISCORD_BOT_TOKEN)
