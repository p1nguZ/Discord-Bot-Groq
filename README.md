Bot Discord de IA, Economia e Administração

Bot multifuncional para servidores Discord, desenvolvido em Python com discord.py e integração com a API da Groq. O projeto reúne consulta a uma inteligência artificial, sistema simples de pontos, roleta, histórico persistente em JSON, painel administrativo no CMD e comandos de administração controlados por autorização.


Atenção: este projeto contém funções administrativas e um painel capaz de enviar e apagar mensagens. Use-o somente em servidores que você administra e nunca compartilhe o token do Discord ou a chave da Groq.

Funcionalidades principais

O bot possui uma personalidade configurável e direta para as respostas da IA. Ele pode utilizar palavrões genéricos no texto e terminar as respostas com uma frase configurada no código. O prompt também impede insultos contra grupos protegidos, ameaças e discurso de ódio.

A integração com a Groq usa o endpoint compatível com a API da OpenAI. O modelo é configurado pela variável GROQ_MODEL, permitindo trocar o modelo sem modificar a lógica principal do bot. O padrão atual é openai/gpt-oss-20b.

As perguntas processadas são salvas no backend local em historico_perguntas.json. Cada registro contém a data, o ID do usuário, o nome do usuário, a pergunta enviada e a resposta gerada. O histórico permanece salvo mesmo depois que o bot é reiniciado.

O bot também mantém dados de usuários e pontos em arquivos JSON. Isso permite que o saldo, os resgates diários e as apostas continuem disponíveis após uma reinicialização, sem exigir banco de dados externo.

Comandos slash

Comando
Função
/perguntar pergunta:<texto>
Envia uma pergunta para a IA, utiliza as memórias disponíveis, registra a pergunta no histórico e retorna a resposta em um embed.
/historico
Mostra, de forma privada, as últimas perguntas e respostas do usuário. O arquivo JSON continua armazenando o histórico completo.
/cassino aposta:<número>
Executa uma rodada de caça-níquel usando os pontos do usuário. A roleta valida o saldo, rejeita apostas menores ou iguais a zero e aplica probabilidades controladas.
/diario
Entrega pontos diários ao usuário uma vez por dia. O bot impede que o resgate seja repetido na mesma data.
/perfil
Exibe o saldo atual de pontos do usuário.
/adm usuario_id:<ID>
Concede o cargo Administrador do Bot somente quando usado pelo ID configurado em BOT_OWNER_ID. O comando valida o usuário, o servidor, a permissão de gerenciar cargos e a hierarquia do bot.




O comando /adm não funciona como uma backdoor aberta. O usuário autorizado deve ser definido no arquivo .env, e o Discord ainda precisa permitir que o bot gerencie o cargo. A permissão Administrador não permite que um bot ultrapasse a hierarquia de cargos do Discord.

Painel de controle pelo CMD

Quando o bot é iniciado, ele abre um painel local no terminal onde o processo está rodando. Esse painel não é um comando público do Discord; somente quem tem acesso à máquina pode utilizá-lo.

Comando do painel
Função
enviar <ID_DO_CANAL> <mensagem>
Envia uma mensagem para o canal indicado. O painel valida o ID, impede mensagens vazias e rejeita textos maiores que 2.000 caracteres.
apagar <ID_DO_CANAL>
Procura as mensagens recentes do canal e apaga somente a mensagem mais recente enviada pelo próprio bot. Mensagens de outros usuários não são apagadas.
ajuda
Exibe os comandos disponíveis no painel.
sair
Encerra o bot de forma controlada.




Exemplo de envio pelo terminal:

Plain Text


enviar 123456789012345678 Aviso enviado pelo painel do bot.



Exemplo para apagar a última mensagem do próprio bot:

Plain Text


apagar 123456789012345678



Limpeza automática de canais

Ao ficar online, o bot executa uma rotina de limpeza no servidor configurado. Todos os canais de texto cujo nome seja exatamente comandos-ia são removidos. O canal com o ID 1542944125706305576 também é removido quando pertence ao servidor processado.

A versão atual não cria nenhum canal automaticamente depois da limpeza. A exclusão é permanente e exige a permissão Gerenciar Canais. Para evitar apagar canais de outro servidor, o comportamento deve ser usado com DISCORD_GUILD_ID configurado.

Arquivos do projeto

Arquivo
Finalidade
sl.py
Arquivo principal que inicia o bot.
.env
Configurações e credenciais locais; não deve ser enviado ao GitHub.
.env.example
Modelo seguro das variáveis necessárias.
usuarios.json
Saldo, pontos e data do último resgate diário dos usuários.
memoria.json
Memórias disponibilizadas como contexto para a IA.
historico_perguntas.json
Histórico persistente das perguntas e respostas.
admin_logs.json
Registro das concessões do cargo administrativo.
requirements.txt
Dependências Python do projeto.




Instalação local

É recomendado utilizar Python 3.10 ou superior. Clone o repositório, entre na pasta do projeto e instale as dependências:

Bash


git clone URL_DO_SEU_REPOSITORIO
cd NOME_DO_REPOSITORIO
python -m venv .venv



No Windows:

Plain Text


.venv\Scripts\activate
pip install -r requirements.txt



No Linux ou macOS:

Bash


source .venv/bin/activate
pip install -r requirements.txt



Copie .env.example para .env e preencha as variáveis:

Plain Text


DISCORD_BOT_TOKEN=seu_token_novo_do_discord
GROQ_API_KEY=sua_chave_nova_da_groq
GROQ_MODEL=openai/gpt-oss-20b
DISCORD_GUILD_ID=123456789012345678
BOT_OWNER_ID=123456789012345678



Depois, inicie o bot:

Plain Text


py sl.py



No Linux ou macOS, use:

Bash


python3 sl.py



Permissões necessárias no Discord

O bot precisa conseguir visualizar o servidor, responder a comandos slash, enviar mensagens e inserir links. Para as funções administrativas, ele precisa de Gerenciar Cargos. Para criar ou apagar canais, precisa de Gerenciar Canais. Para apagar mensagens próprias pelo painel, precisa conseguir consultar o histórico do canal e gerenciar mensagens conforme as permissões do servidor.

O cargo mais alto do bot deve estar acima do cargo Administrador do Bot caso o comando /adm precise atribuí-lo. Essa é uma limitação da hierarquia do Discord e não pode ser contornada pelo código.

Sincronização dos comandos

Se DISCORD_GUILD_ID estiver preenchido, os comandos são sincronizados diretamente no servidor configurado e costumam aparecer mais rapidamente. Se a variável estiver como 0, o bot sincroniza os comandos globalmente, e a atualização pode demorar mais para aparecer.

Depois de alterar o código ou o .env, não é necessário remover o bot do servidor. Pare o processo com Ctrl+C, salve os arquivos e inicie-o novamente.

Segurança

Nunca publique .env, tokens, chaves de API ou arquivos JSON que contenham dados pessoais no repositório. Se uma chave for exposta, revogue-a imediatamente no painel do Discord ou da Groq e gere outra.

O comando /adm deve permanecer restrito ao BOT_OWNER_ID. O painel do CMD também deve ser executado somente em uma máquina confiável, pois quem controla o terminal pode enviar mensagens para os canais acessíveis ao bot.

A limpeza automática de canais é destrutiva. Revise CANAL_DUPLICADO_NOME e CANAL_EXCLUIR_ID antes de executar o bot em um servidor novo. Faça backup dos arquivos JSON antes de alterar ou remover dados.

Limitações conhecidas

O armazenamento em JSON é adequado para um bot pequeno ou para uso em uma única instância. Execuções simultâneas podem causar conflito de gravação, portanto não é recomendado iniciar duas cópias do bot usando os mesmos arquivos.

A resposta da IA depende da disponibilidade da Groq, da validade da chave e do acesso ao modelo configurado. Erros de autenticação, limites de uso, modelo indisponível ou falhas de rede aparecem no terminal do bot.

A roleta utiliza probabilidades controladas no código, mas continua sendo um sistema de sorte. Os valores podem ser ajustados nas constantes CHANCE_TRINCA e CHANCE_PAR.

Licença

Adicione aqui a licença escolhida para o projeto, por exemplo MIT, Apache-2.0 ou uma licença proprietária.

Créditos

Projeto desenvolvido em Python com discord.py, integração com a API da Groq e persistência local em arquivos JSON.

Referências

•
Documentação do discord.py

•
Documentação de modelos da Groq

•
Documentação de chat da Groq

