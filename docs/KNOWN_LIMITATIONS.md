# Limitações conhecidas

Este documento registra limitações do NutEV Reference Engine que devem permanecer explícitas na documentação e na interpretação dos outputs.

## 1. O ranking não é avaliação de qualidade científica

O score prioriza leitura por sinais de texto, taxonomia, tipo documental, provider, identificadores e recência.

Ele não mede diretamente:

- risco de viés;
- qualidade metodológica;
- certeza da evidência;
- aplicabilidade clínica;
- elegibilidade para uma revisão;
- força de recomendação.

Um registro com score maior pode ser menos importante para uma pergunta específica do que um registro com score menor.

## 2. A deduplicação não é semântica

A identidade atual usa:

```text
DOI -> PMID -> URL -> título normalizado
```

Consequências:

- o mesmo conteúdo publicado em veículos diferentes pode permanecer em mais de um registro;
- versões, republicações, documentos irmãos ou consensos publicados em periódicos distintos podem aparecer separados;
- títulos quase idênticos com identificadores diferentes não são automaticamente agrupados;
- `records_unique == records_input` não prova ausência de duplicatas conceituais.

## 3. Matching de taxonomia é aditivo

Um documento que corresponde a muitos grupos e termos pode acumular score elevado mesmo quando não é o documento mais central para o objetivo do usuário.

A taxonomia deve ser interpretada como mecanismo de recuperação e priorização, não como ontologia de qualidade da evidência.

## 4. Nomes de grupos de taxonomia são caminhos de configuração

Os outputs exibem caminhos dos grupos carregados de `keyword_taxonomy*.json` para auditabilidade.

Esses nomes podem refletir a organização histórica dos arquivos de configuração. Eles não são categorias formais de qualidade científica e não devem ser citados como classificação metodológica externa.

## 5. Tipos documentais são inferidos por texto do título

Os bônus de guideline, consensus, systematic review e termos relacionados são ativados por expressões no título.

Isso pode produzir:

- sobreposição de bônus quando termos se contêm mutuamente;
- classificação textual de documentos que discutem guidelines sem serem, eles próprios, guidelines;
- ausência de bônus quando o tipo documental não aparece no título.

## 6. Metadados variam entre providers

Os providers não oferecem o mesmo nível de detalhe para:

- abstracts;
- autores;
- keywords;
- identificadores;
- datas;
- URLs de texto completo;
- tipo documental.

Essa assimetria pode influenciar o ranking.

## 7. Limites de coleta não equivalem a exaustividade

O perfil operacional usa limites máximos por provider. O perfil profundo aumenta esses limites, mas também não constitui garantia de cobertura exaustiva.

Cobertura depende de:

- consulta configurada;
- disponibilidade da API/interface;
- paginação e limites do provider;
- rate limits;
- credenciais;
- indexação do provider;
- idioma e metadados disponíveis.

## 8. BVS/LILACS e SciELO podem bloquear automação

As interfaces públicas nativas podem responder com `401` ou `403`.

A `main` atual registra esse estado como `unavailable` e continua quando há outras fontes disponíveis.

`unavailable` não significa “zero resultados”. Significa que o engine não conseguiu obter resultados por aquela rota automatizada naquela execução.

## 9. Providers opcionais dependem de credenciais

Google Programmable Search, Brave e SerpAPI só são executados quando as credenciais necessárias estão presentes no ambiente.

A ausência dessas fontes deve ser tratada como diferença de cobertura da execução.

## 10. Scopus e Web of Science não são simulados

Sem integração/licença configurada, essas bases não fazem parte da coleta real. O engine não substitui seus resultados por resultados de outra fonte com o mesmo rótulo.

## 11. Recência é um bônus leve, não um filtro

Documentos recentes recebem um pequeno bônus, mas documentos antigos podem continuar no topo quando têm muitos sinais temáticos.

## 12. URLs podem apontar para recursos externos mutáveis

O engine preserva URLs recebidas dos providers. Esses endereços podem:

- expirar;
- redirecionar;
- mudar de política de acesso;
- apontar para PDF, landing page ou repositório externo.

O repositório não redistribui automaticamente o conteúdo protegido desses links.

## 13. O TOP N é uma janela de visualização

`TOP_REFERENCIAS.md` apresenta somente o TOP N configurado, atualmente 100 por padrão.

`reference_ranking.csv` e `reference_ranking.jsonl` contêm o conjunto ranqueado completo disponível para aquela execução.

## 14. Uma execução validada não garante resultados futuros idênticos

A execução registrada em 18/08/2026 teve 8.702 entradas no ranking e 115 grupos de taxonomia carregados. Resultados futuros podem mudar porque providers e metadados externos mudam com o tempo.

Para reprodutibilidade, registre o SHA do repositório, preserve `latest.json`, manifests e os arquivos de entrada usados pelo ranker.

## 15. Uso recomendado

Use o engine para:

1. descoberta ampla;
2. priorização de leitura;
3. inspeção humana;
4. curadoria de duplicatas/versões;
5. seleção científica conforme critérios externos ao ranking.

Não use o ranking sozinho como justificativa de inclusão ou exclusão científica.
