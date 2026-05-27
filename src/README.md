# API de Atividades da Mergington High School

Uma aplicação FastAPI super simples que permite aos alunos visualizar e se inscrever em atividades extracurriculares.

## Funcionalidades

- Visualizar todas as atividades extracurriculares disponíveis
- Inscrever-se em atividades
- Visualizar anuncios ativos no topo da tela
- Gerenciar anuncios (criar, editar e excluir) para usuarios logados

## Como começar

1. Instale as dependências:

   ```
   pip install fastapi uvicorn
   ```

2. Execute a aplicação:

   ```
   python app.py
   ```

3. Abra seu navegador e acesse:
   - Documentação da API: http://localhost:8000/docs
   - Documentação alternativa: http://localhost:8000/redoc

## Endpoints da API

| Método | Endpoint                                                          | Descrição                                                            |
| ------ | ----------------------------------------------------------------- | -------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Obtém todas as atividades com detalhes e número atual de participantes |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Inscreve-se em uma atividade                                         |
| GET    | `/announcements/active`                                           | Lista anuncios ativos para exibicao publica                          |
| GET    | `/announcements?teacher_username=<usuario>`                       | Lista todos os anuncios para gerenciamento (requer login)            |
| POST   | `/announcements?teacher_username=<usuario>`                       | Cria um anuncio (requer data de expiracao)                           |
| PUT    | `/announcements/{announcement_id}?teacher_username=<usuario>`     | Atualiza um anuncio existente                                        |
| DELETE | `/announcements/{announcement_id}?teacher_username=<usuario>`     | Exclui um anuncio                                                    |

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:
   - Descrição
   - Horário
   - Número máximo de participantes permitidos
   - Lista de e-mails dos alunos inscritos

2. **Alunos** - Usa o e-mail como identificador:
   - Nome
   - Série

Os dados sao armazenados no MongoDB local usado pela aplicacao.
