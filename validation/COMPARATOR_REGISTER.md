# Comparator Register

Data de levantamento inicial: 2026-08-18

Este arquivo registra comparadores potenciais para o benchmark. Descrições de produto abaixo vêm de documentação oficial dos próprios fornecedores/projetos e, portanto, devem ser tratadas como `VENDOR_OR_PROJECT_REPORTED` até reprodução independente no protocolo NutEV.

## ASReview LAB

Fonte oficial: https://asreview.nl/

Capacidades relevantes para comparação:

- priorização de screening por active learning;
- simulation mode com datasets rotulados;
- métricas de recall/work saved/time to discovery;
- software open source e fluxo researcher-in-the-loop.

Uso no benchmark NutEV: comparador de priorização/screening quando o mesmo corpus rotulado puder ser importado de forma reprodutível.

## Rayyan

Fonte oficial: https://www.rayyan.ai/

Capacidades relevantes para comparação:

- importação/organização de referências;
- deduplicação;
- title/abstract screening;
- priorização assistida;
- trilha/auditoria de revisão.

Uso no benchmark NutEV: comparador operacional de organização, deduplicação e priorização quando houver exportação comparável.

## Elicit Systematic Review

Fonte oficial: https://elicit.com/solutions/literature-review

Capacidades relevantes para comparação:

- busca;
- screening;
- extração;
- priorização por critérios;
- avaliações próprias publicadas pelo fornecedor.

Uso no benchmark NutEV: comparador externo quando a versão/configuração puder ser registrada. Métricas publicadas pelo fornecedor não devem ser reutilizadas como resultado NutEV.

## Covidence

Fonte oficial: https://www.covidence.org/

Capacidades relevantes para comparação:

- gerenciamento de revisão;
- preparação/deduplicação;
- screening;
- resolução de conflitos;
- extração e fluxos posteriores.

Uso no benchmark NutEV: comparador de workflow, não necessariamente comparador algorítmico direto de retrieval.

## ResearchRabbit

Fonte oficial: https://www.researchrabbit.ai/

Capacidades relevantes para comparação:

- descoberta por redes de citação;
- navegação de trabalhos relacionados;
- estratégia de descoberta complementar a busca lexical.

Uso no benchmark NutEV: avaliar se exploração por rede recupera referências-chave que o pipeline lexical/multifonte NutEV não encontra.

## Baselines internos obrigatórios

Independentemente das ferramentas externas, o NutEV deve vencer ou justificar-se contra baselines reproduzíveis que não dependem de produto comercial:

1. PubMed ordenação nativa;
2. união sem ranking NutEV;
3. lexical simples;
4. recência;
5. ablations do próprio NutEV.

## Regra de comparabilidade

Nenhuma ferramenta externa deve ser declarada superior ou inferior com base em páginas de marketing. O veredito exige corpus, pergunta e labels comparáveis, com versão/configuração registradas e métricas calculadas pelo mesmo protocolo sempre que tecnicamente possível.
