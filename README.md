# RiosFootball

Site de vitrine e pedidos da loja de camisas de futebol **RiosFootball**, feito para aprender desenvolvimento web
com HTML, CSS, JavaScript e Python.

## O que o site faz

- Vitrine com busca, filtros por time e tamanho, e página própria de cada camisa (galeria de fotos, tabela de medidas, avaliações e recomendações)
- Menu com painel de times por liga, com escudo e página de cada time
- Conta de cliente (cadastro com e-mail ou entrada com Google) e acompanhamento dos pedidos
- Carrinho e pedido enviado pelo WhatsApp, com número de pedido e status (aguardando pagamento, pago, em separação, enviado, entregue, finalizado)
- Avaliações de clientes que compraram, com nota, texto, fotos e vídeo
- Painel do dono: pedidos por dia, cadastro, edição e exclusão de times e produtos (com várias fotos), moderação de avaliações e troca de senha

## Tecnologias

- **Front-end:** HTML, CSS e JavaScript (sem frameworks)
- **Back-end:** Python com Flask
- **Banco de dados:** SQLite
- **Login com Google:** Google Identity Services, com verificação do token no servidor

## Estrutura

```
backend/    servidor Flask (app.py), banco de dados (banco.py) e páginas privadas do painel
frontend/   páginas, estilos, scripts e imagens do site
rodar.bat   liga o servidor no Windows (cria o ambiente e instala as bibliotecas na primeira vez)
```

## Como rodar no Windows

1. Instale o Python 3 (marque a opção "Add python.exe to PATH").
2. Dê dois cliques em `rodar.bat`.
3. Abra `http://localhost:5000` no navegador.

Na primeira execução o banco é criado com dados de exemplo e um usuário `admin` com **senha provisória**.
Entre em `/admin` e use **Trocar senha** imediatamente.

## Login com Google (opcional)

Crie um ID de cliente OAuth do tipo "Aplicativo da Web" no Google Cloud, adicione `http://localhost:5000` nas origens
autorizadas e cole o ID em `backend/config_google.txt` (o arquivo é criado na primeira execução). Sem isso o botão
do Google simplesmente não aparece.

## Segurança

Estes arquivos ficam só na máquina e **não** são enviados ao repositório (veja o `.gitignore`):
`backend/loja.db` (clientes e pedidos), `backend/segredo.key` (chave do login), `backend/config_google.txt` e `backend/uploads/` (fotos).

## Status

Em desenvolvimento. Ainda não publicado na internet.
