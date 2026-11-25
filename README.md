# ⚓ Alerta de Filmes

Avisa por e-mail quando um filme da sua lista **já dá para assistir no Nuvio**.

Você cadastra os filmes que está esperando como **Issues** deste repositório. De tempos em tempos, o GitHub Actions consulta o AIOStreams (o mesmo addon que o Nuvio usa) e, quando o filme tem streams bons suficientes, manda um e-mail, comenta na Issue e a fecha.

---

## Como funciona

1. Cada **Issue aberta** é um filme da lista. O título é o nome do filme.
2. O workflow roda a cada 6 horas (e quando você clica em *Run workflow*).
3. Para cada Issue aberta, o script:
   - descobre o ID do IMDb do filme (busca no Cinemeta);
   - pergunta ao AIOStreams quais streams existem;
   - descarta versões de baixa qualidade (CAM, TS, TELESYNC etc.);
   - se sobraram **2 ou mais** streams bons, envia o e-mail.
4. Depois de avisar, comenta na Issue e a **fecha**. Issue fechada = já avisado. Não existe arquivo de estado.

Na primeira vez que vê uma Issue, o script também comenta qual filme entendeu (nome, ano e ID) e coloca o rótulo `conferido`, para você checar se ele pegou o filme certo.

## Arquivos

```
alerta_filmes.py              ← o script
.github/workflows/alerta.yml  ← o agendamento (GitHub Actions)
README.md                     ← este arquivo
```

A pasta se chama `.github` (com o ponto) e `workflows` (no plural). Se o nome estiver diferente, o GitHub ignora o workflow.

---

## Configuração (uma vez só)

### 1. Repositório

Use um repositório **privado** e deixe as **Issues** ativadas (Settings → General → Features).

### 2. Permissões do workflow

Em `alerta.yml`, o bloco de permissões precisa ter as duas linhas:

```yaml
permissions:
  contents: read
  issues: write
```

Sem `contents: read`, o passo de checkout falha com "repository not found".

### 3. Senha de app do Gmail

O envio usa o Gmail com uma **senha de app** (não a senha normal da conta).

1. Ative a **verificação em duas etapas** na conta Google que vai enviar os e-mails.
2. Abra `myaccount.google.com/apppasswords`, dê um nome (ex.: "alerta filmes") e crie.
3. Copie a senha de 16 caracteres, sem os espaços. Ela só aparece uma vez.

A senha de app só funciona junto com a conta que a gerou.

### 4. URL do AIOStreams

No site de configuração do seu AIOStreams, na aba de instalação, copie o link do manifest. Ele termina em `/manifest.json`. Esse link dá acesso à sua configuração: guarde só nos secrets, nunca no código nem numa Issue.

### 5. Secrets

Em **Settings → Secrets and variables → Actions → New repository secret**, crie (use *Repository secrets*, com os nomes exatamente assim):

| Nome | O que colocar |
|---|---|
| `AIOSTREAMS_MANIFEST_URL` | Link do manifest do AIOStreams (termina em `/manifest.json`) |
| `GMAIL_USER` | Gmail que envia os avisos |
| `GMAIL_APP_PASSWORD` | Senha de app de 16 caracteres, sem espaços |
| `EMAIL_TO` | Quem recebe os avisos. Opcional: se faltar, vai para o `GMAIL_USER`. Vários endereços separados por vírgula |

### 6. Primeiro teste

1. Crie uma Issue com um filme que você sabe que já está no Nuvio.
2. Vá em **Actions → Alerta de filmes → Run workflow**.
3. Abra a execução → job **checar** → passo **Checar filmes da lista** para ver o log.

---

## Como usar no dia a dia

### Adicionar um filme

Aba **Issues → New issue**, com o nome do filme no título. O corpo pode ficar vazio.

- `Duna Parte Dois` funciona na maioria dos casos.
- Para filmes com nome parecido, acrescente o ano: `Dune 2024`.
- Se o filme certo não for encontrado, use o ID do IMDb no título: `Dune: Part Two tt15239678`.
- A busca é feita no Cinemeta, que é em inglês. Se um título em português não achar nada, tente o nome original.

### Receber o aviso

Quando o filme tiver pelo menos 2 streams bons, chega o e-mail e a Issue é fechada. Para acompanhar outro filme, abra outra Issue.

### Quando os avisos chegam

O workflow roda às **00h, 06h, 12h e 18h em UTC**, o que equivale a 21h, 03h, 09h e 15h em Campina Grande (UTC-3). O atraso máximo entre o filme ficar disponível e o aviso é de cerca de 6 horas, e o GitHub pode atrasar execuções agendadas por alguns minutos.

### Rodar na hora

**Actions → Alerta de filmes → Run workflow**.

---

## Ajustes comuns

### Mínimo de streams bons

No `alerta.yml`, em `MIN_STREAMS`. Valor maior = mais exigente (menos alarmes falsos, aviso mais tardio).

### Horários

Troque a linha do cron no `alerta.yml`. O cron usa UTC. Alguns exemplos:

| Cron | Quando roda |
|---|---|
| `0 */6 * * *` | A cada 6 horas (padrão) |
| `0 11,15,19,23 * * *` | 8h, 12h, 16h e 20h no horário de Campina Grande |
| `0 * * * *` | De hora em hora |

Em repositório privado, o plano gratuito tem 2.000 minutos de Actions por mês. Rodar de hora em hora fica em torno de 720 execuções mensais, e cada uma dura poucos segundos a cerca de 1 minuto. Evite frequências muito maiores.

### Texto e visual do e-mail

No `alerta_filmes.py`, na função `main`, o assunto e o corpo ficam na chamada `send_mail(...)`, e o HTML do e-mail fica na variável `corpo_html`. As variáveis disponíveis são `{nome}`, `{imdb}` e `{len(streams)}`. Os estilos ficam dentro de cada elemento (`style="..."`), porque o Gmail ignora CSS externo.

### Nome do remetente

Na função `send_mail`, a linha do `From` usa `formataddr(("Nome que você quiser", GMAIL_USER))`. Se o Gmail continuar mostrando o nome antigo, mude o nome na conta Google que envia.

### Vários destinatários

No secret `EMAIL_TO`, separe os endereços por vírgula. Para que ninguém veja os endereços dos outros, use `Bcc` no lugar de `To` dentro de `send_mail`:

```python
msg["To"] = GMAIL_USER
msg["Bcc"] = EMAIL_TO
```

Quem quiser abrir Issues no repositório precisa ser colaborador (Settings → Collaborators).

### Menos e-mails do GitHub

Os e-mails do GitHub sobre comentários e fechamento das Issues são notificações normais do repositório. Para reduzi-los, use o botão **Watch → Ignore** ou um filtro no Gmail para `notifications@github.com`. Eles não têm relação com o e-mail de alerta do script.

---

## Criar Issue por e-mail

O script agora lê a caixa de entrada do Gmail (IMAP) e transforma e-mails em Issues: o **assunto** vira o título. Só valem e-mails de remetentes listados em `EMAIL_TO`, e os avisos do próprio script (assunto começando com "Ahoy") são ignorados. O e-mail só é lido quando o workflow roda, então há o mesmo atraso do agendamento.

---

## Problemas comuns

| Sintoma | Provável causa e solução |
|---|---|
| Aba Actions mostra "No workflows found" | O arquivo não está em `.github/workflows/alerta.yml`. Confira o ponto no começo e o plural em `workflows`. |
| Falha no passo de checkout, "repository not found" | Falta `contents: read` em `permissions` no `alerta.yml`. |
| `KeyError: 'NOME_DO_SECRET'` | O secret não existe ou foi criado com nome diferente. Os nomes precisam ser idênticos à tabela acima. |
| `SMTPAuthenticationError` | Senha de app errada ou com espaços, ou `GMAIL_USER` não é a conta que gerou a senha. |
| `apppasswords` diz que a configuração não está disponível | Falta ativar a verificação em duas etapas, ou a conta é de trabalho/escola, ou a Proteção Avançada está ligada. |
| `AIOSTREAMS_MANIFEST_URL deve terminar em /manifest.json` | A URL do secret está incompleta ou tem algo depois de `manifest.json`. |
| `HTTP Error 403` nas chamadas ao GitHub | Em Settings → Actions → General → *Workflow permissions*, marque "Read and write permissions". |
| "não encontrei no Cinemeta" | Use o nome original do filme, o ano ou o ID do IMDb no título. |
| Filme certo, mas nunca avisa | Veja no log quantos streams foram contados. Com 0 ou 1, o mínimo não é atingido ou o filtro está descartando demais. |
| Filme errado foi entendido | Edite o título da Issue com o ano ou o ID do IMDb. |
| Agendamento parou de rodar | O GitHub pausa agendamentos em repositórios sem atividade por muito tempo. Reative em Actions. |

O log de qualquer execução fica em **Actions → (execução) → checar → Checar filmes da lista**.
