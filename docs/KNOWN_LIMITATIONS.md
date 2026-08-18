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

## 3. Matching de taxonomia continua aditivo, embora agora possua cap

Um documento que corresponde a muitos grupos e termos acumula score até o teto configurado.

A `main` com guardrails usa `taxonomy_score_cap = 60`, o que reduz inflação estrutural, mas não elimina completamente o efeito da organização da taxonomia.

A taxonomia deve ser interpretada como mecanismo de recuperação e priorização, não como ontologia de qualidade da evidência.

## 4. Nomes de grupos de taxonomia são caminhos de configuração

Os outputs exibem caminhos dos grupos carregados de `keyword_taxonomy*.json` para auditabilidade.

Esses nomes podem refletir a organização histórica dos arquivos de configuração. Eles não são categorias formais de qualidade científica e não devem ser citados como classificação metodológica externa.

O cap de taxonomia reduz, mas não elimina, a influência da fragmentação histórica em grupos.

## 5. Tipos documentais são inferidos por texto do título

Os bônus de guideline, consensus, systematic review e termos relacionados são ativados por expressões no título.

A política atual evita empilhamento de expressões sobrepostas: todos os hits são registrados, mas apenas o maior peso é aplicado.

Ainda podem ocorrer:

- classificação textual de documentos que discutem guidelines sem serem, eles próprios, guidelines;
- ausência de bônus quando o tipo documental não aparece no título;
- ambiguidade lexical em títulos curtos.

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

## 7. Rastreabilidade não prova verdade científica

As classes `A_IDENTIFIER` e `B_TRACEABLE_URL` significam que o registro possui uma rota de rastreamento independente por identificador ou URL.

Isso não prova que:

- o provider não cometeu erro bibliográfico;
- DOI/PMID/URL corresponde ao documento esperado;
- o abstract esteja correto;
- as conclusões científicas sejam verdadeiras;
- o documento tenha qualidade metodológica.

O guardrail protege proveniência e integridade do pipeline, não substitui leitura crítica.

## 8. Hash de integridade não autentica o provider externo

`master_records_sha256` e os hashes de output detectam alterações do arquivo depois de ele ser produzido.

Eles não constituem assinatura criptográfica do PubMed, Crossref, OpenAlex ou outro provider. Um arquivo pode ser íntegro em relação ao manifesto e ainda conter um erro originado no serviço externo.

## 9. A quarentena pode reduzir recall

Por padrão, registros sem provider/título ou sem DOI/PMID/PMCID/URL HTTP(S) não são ranqueados.

Isso é intencional para evitar que itens não rastreáveis apareçam como referências priorizadas, mas pode excluir registros bibliograficamente reais com metadados incompletos.

Esses itens ficam em:

```text
reference_quarantine.jsonl
```

A correção deve ser baseada no dado-fonte, nunca em preenchimento por suposição.

## 10. Limites de coleta não equivalem a exaustividade

O perfil operacional usa limites máximos por provider. O perfil profundo aumenta esses limites, mas também não constitui garantia de cobertura exaustiva.

Cobertura depende de:

- consulta configurada;
- disponibilidade da API/interface;
- paginação e limites do provider;
- rate limits;
- credenciais;
- indexação do provider;
- idioma e metadados disponíveis.

## 11. BVS/LILACS e SciELO podem bloquear automação

As interfaces públicas nativas podem responder com `401` ou `403`.

A `main` registra esse estado como `unavailable` e continua quando há outras fontes disponíveis.

`unavailable` não significa “zero resultados”. Significa que o engine não conseguiu obter resultados por aquela rota automatizada naquela execução.

## 12. Providers opcionais dependem de credenciais

Google Programmable Search, Brave e SerpAPI só são executados quando as credenciais necessárias estão presentes no ambiente.

A ausência dessas fontes deve ser tratada como diferença de cobertura da execução.

## 13. Scopus e Web of Science não são simulados

Sem integração/licença configurada, essas bases não fazem parte da coleta real. O engine não substitui seus resultados por resultados de outra fonte com o mesmo rótulo.

## 14. Recência é um bônus leve, não um filtro

Documentos recentes recebem um pequeno bônus, mas documentos antigos podem continuar no topo quando têm muitos sinais temáticos.

## 15. URLs podem apontar para recursos externos mutáveis

O engine preserva URLs recebidas dos providers. Esses endereços podem:

- expirar;
- redirecionar;
- mudar de política de acesso;
- apontar para PDF, landing page ou repositório externo.

O repositório não redistribui automaticamente o conteúdo protegido desses links.

## 16. O TOP N é uma janela de visualização

`TOP_REFERENCIAS.md` apresenta somente o TOP N configurado, atualmente 100 por padrão.

`reference_ranking.csv` e `reference_ranking.jsonl` contêm o conjunto elegível ranqueado completo disponível para aquela execução.

Registros em quarentena ficam separados e não estão incluídos nessas contagens de ranking.

## 17. Uma execução validada não garante resultados futuros idênticos

A execução Windows registrada em 18/08/2026 teve 8.702 entradas no ranking e 115 grupos de taxonomia carregados. Ela documenta aquele estado do software e das fontes externas.

As mudanças posteriores de guardrail alteram o contrato do ranking: verificam hashes, aplicam quarentena, caps e scoring não cumulativo para tipo documental. Portanto, os números daquela execução histórica não devem ser tratados como baseline obrigatório da `main` atual.

Resultados futuros podem mudar porque código, política, providers e metadados externos mudam com o tempo.

Para reprodutibilidade, registre o SHA do repositório e preserve `latest.json`, `AUDIT_MANIFEST.json`, manifests e arquivos de entrada.

## 18. Guardrails não eliminam todas as formas possíveis de erro

O sistema reduz risco de referências fabricadas dentro do pipeline determinístico, mas não garante ausência absoluta de:

- erro de provider;
- erro de parser;
- erro de configuração;
- erro de regra de scoring;
- metadados incorretos fornecidos por terceiros.

Por isso existem testes, hashes, quarentena, `score_breakdown` e manifesto de auditoria.

## 19. IA generativa não faz parte do runtime canônico

O Reference Engine atual não usa LLM para gerar referências, preencher metadados, resumir estudos ou produzir recomendações.

Se uma função generativa for adicionada futuramente, ela deverá ter contrato próprio de citação, rastreabilidade, distinção entre extração e inferência e bloqueio quando a fonte necessária estiver ausente.

## 20. Uso recomendado

Use o engine para:

1. descoberta ampla;
2. priorização de leitura;
3. inspeção de rastreabilidade e `score_breakdown`;
4. curadoria humana de duplicatas/versões;
5. seleção científica conforme critérios externos ao ranking.

Não use o ranking sozinho como justificativa de inclusão ou exclusão científica.
