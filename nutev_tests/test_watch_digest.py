from nutev.global_watch.watch_digest import write_digest


def test_digest_contains_resumo_executivo(tmp_path):
    md,_=write_digest([{'title':'t','category':'guidelines_consensus','download_status':'pdf','workstream_affinity':['policy_systems']}], tmp_path/'run', tmp_path/'latest.md')
    txt=md.read_text(encoding='utf-8')
    assert 'Resumo executivo' in txt
    assert 'policy_systems' in txt
    assert 'busca1' not in txt


def test_digest_contains_falhas_limitacoes(tmp_path):
    md,_=write_digest([{'title':'t','category':'guidelines_consensus','download_status':'metadata_only','failure_reason':'http_403','host':'x','workstream_affinity':['policy_systems']}], tmp_path/'run', tmp_path/'latest.md')
    txt=md.read_text(encoding='utf-8')
    assert 'Falhas e limitações' in txt


def test_digest_groups_categories(tmp_path):
    md,_=write_digest([{'title':'t','category':'diet_patterns','download_status':'html_snapshot','workstream_affinity':['policy_systems']}], tmp_path/'run', tmp_path/'latest.md')
    txt=md.read_text(encoding='utf-8')
    assert 'diet_patterns' in txt


def test_digest_contains_statuses(tmp_path):
    rows=[{'title':'a','category':'guidelines_consensus','download_status':'pdf','workstream_affinity':['policy_systems']},{'title':'b','category':'guidelines_consensus','download_status':'html_snapshot','workstream_affinity':['policy_systems']},{'title':'c','category':'guidelines_consensus','download_status':'metadata_only','workstream_affinity':['policy_systems']}]
    md,_=write_digest(rows, tmp_path/'run', tmp_path/'latest.md')
    txt=md.read_text(encoding='utf-8')
    assert 'PDFs capturados' in txt and 'HTML snapshots' in txt and 'metadata-only' in txt
