🤖 Bot Discord IA
Bot para Discord com inteligência artificial, sistema de pontos, roleta, histórico de perguntas, comandos administrativos e painel de mensagens pelo CMD.
⚙️ Como fazer funcionar
Instale o Python 3.10 ou superior.
Instale as dependências:
Bash
pip install discord.py requests
Crie um bot no Discord Developer Portal, copie o token e convide o bot para o servidor com os comandos slash e as permissões necessárias.
Crie uma chave da API no console da Groq.
Deixe apenas estes dois arquivos na pasta:
text
main.py
.env
Configure o arquivo .env:
env
DISCORD_BOT_TOKEN=seu_token_do_discord
GROQ_API_KEY=sua_chave_da_groq
GROQ_MODEL=openai/gpt-oss-20b
DISCORD_GUILD_ID=id_do_servidor
BOT_OWNER_ID=seu_id_do_discord
Inicie o bot:
Bash
python main.py
No Windows também pode usar:
bat
py main.py
✨ Funções
🧠 Perguntas para a IA
📚 Histórico de perguntas
💰 Sistema de pontos
🎁 Bônus diário
🎰 Roleta
👤 Perfil de usuário
🔐 Comando /adm
💬 Painel de mensagens pelo CMD
🗑️ Exclusão de mensagens do próprio bot
📝 Registro de ações administrativas
Os arquivos usuarios.json, memoria.json, historico_perguntas.json e admin_logs.json são criados automaticamente pelo bot durante o uso.
