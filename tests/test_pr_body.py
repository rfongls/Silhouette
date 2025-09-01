from silhouette_core.patch.pr_body import compose_pr_body


def test_compose_pr_body_contains_sections():
    goal = 'remove unused param'
    impact = {
        'modules': ['src/util.py'],
        'tests': {'must_run': ['tests/test_util.py'], 'suggested': []},
        'docs': {'suggested': ['services/api/README.md']},
    }
    summary = {'files_changed': ['src/util.py'], 'insertions': 1, 'deletions': 0}
    body = compose_pr_body(goal, impact, summary)
    assert 'Context / Goal' in body
    assert goal in body
    assert 'src/util.py' in body
    assert 'pytest -q tests/test_util.py' in body
    assert '- [ ] CI passes' in body
