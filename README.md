# Exportar objetos do SIIA para o Google Earth

Este documento mostra como utilizar esta ferramenta transformar os objetos em que clica no mapa do SIIA (CVPs, postes, traçado aéreo, condutas, entre outros) num ficheiro KMZ para abrir e editar no Google Earth.

## Checklist antes de começar

-Tenho o Python 3 instalado (python.org/downloads; no instalador, marcar "Add python.exe to PATH") Para confirmar, abrir a linha de comandos (`cmd`) e escrever `python --version`. Deve aparecer um número de versão. Há outras formas de instalar o python.

-Tenho acesso à SIIA, através de credenciais. Os utilizadores são responsáveis por seguir os termos de uso da ANACOM.

-Tenho o ficheiro `siia_to_kml.py` numa pasta, por exemplo `C:\siia`

<https://github.com/tomasmmdf/SIIA-to-KMZ/tree/main>

## Como usar

1. Abrir o SIIA no navegador e iniciar sessão.
2. Premir F12 e abrir o separador **Rede** (Network). Ativar **Preservar registo** (Keep log no Chrome em inglês).
3. No mapa, clicar em cada CVP, poste ou objeto que quer exportar. Cada click também carrega as condutas e troço aéreo ligadas.
4. Carregar no botão assinalado na imagem abaixo, para exportar os objetos clickados (Export HAR (sanitized)). Guardar na pasta do script, com o nome `captura.har`. &#91;image: image.png\]
5. Abrir a pasta , por exemplo `C:\siia`,em que se gravou o .py e o ficheiro .har de captura no Explorador de Ficheiros, clicar na barra de endereço, escrever `cmd` e premir Enter. Alternativamente, navegar para esta pasta na cmd.
6. Escrever `python siia_to_kml.py captura.har -o nome_ficheiro_destino.kmz` e premir Enter.
7. Abrir o ficheiro `nome_ficheiro_destino.kmz` com duplo clique. Abre no Google Earth com uma pasta por camada; ao clicar num ponto ou linha aparecem todos os dados (entidade, freguesia, dimensões, etc.).
8. Alterar os nomes, símbolo e cor dos elementos,  consoante a necessidade. Limpar  os resultados no Earth, removendo o que não queremos, e confirmar as localizações.
9. Apagar o ficheiro `captura.har`. Contém dados de sessão, por isso não partilhar nem enviar por email.

## Resolução de problemas

| Problema | O que fazer |
| --- | --- |
| `python` não é reconhecido cmd | Escrever `py` em vez de `python`. Se continuar, reinstalar o Python e marcar "Add python.exe to PATH". |
| "No MapServer query responses found",&#32; ou .har ficou com 0 kb | O HAR não tem os cliques. Dar reload à página, dar clear aos logs. Repetir os passos 2 a 4 sem fechar o separador Rede. |
| Ficheiro não encontrado | O nome tem de ser igual ao do ficheiro guardado (incluindo `.har`) e estar na mesma pasta que o script. |
| Só aparecem alguns objetos | Só são exportados os objetos em que clicou. Clicar nos que faltam e guardar um novo HAR. |
| Uso Mac | Abrir o Terminal e usar `python3` em vez de `python`. |
| Quero adicionar objetos a um kmz já existente | Dar reload na página, clear logs, repetir 2 a 4. Gravar com um nome de .har diferente e adaptar a linha `python siia_to_kml.py captura123.har -o siia123.kmz`. Abrir o novo kmz com o velho e depois arrastar os elementos para a mesma pasta. |
|  |  |
