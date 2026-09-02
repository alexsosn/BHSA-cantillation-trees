from bhsa_cantillation.metrics import tree_features


def leaf(accent="A"):
    return {"path": "0", "slots": [1, 1], "text": "x", "accent": accent}


def node(left, right, accent="A"):
    return {"accent": accent, "children": [left, right]}


def test_balanced_tree_metrics_and_signatures():
    tree = node(
        node(leaf("Tipcha"), leaf("Atnach"), "Tipcha"),
        node(leaf("Tipcha"), leaf("Sof Pasuq"), "Tipcha"),
        "Atnach",
    )
    assert tree_features(tree) == {
        "cantillation_shape": "((L,L),(L,L))",
        "cantillation_branch_signature": "Atnach(Tipcha(L,L),Tipcha(L,L))",
        "cantillation_accent_signature": (
            "Atnach(Tipcha(Tipcha,Atnach),Tipcha(Tipcha,Sof_Pasuq))"
        ),
        "cantillation_depth": 2,
        "cantillation_leaf_count": 4,
        "cantillation_mean_leaf_depth": "2",
        "cantillation_colless": 0,
        "cantillation_colless_normalized": "0",
        "cantillation_sackin": 8,
        "cantillation_longest_ladder": 0,
        "cantillation_longest_accent_run": 2,
        "cantillation_depth_leaf_ratio": "0.5",
    }


def test_maximally_imbalanced_four_leaf_tree():
    tree = node(leaf(), node(leaf(), node(leaf(), leaf())))
    metrics = tree_features(tree)
    assert metrics["cantillation_depth"] == 3
    assert metrics["cantillation_leaf_count"] == 4
    assert metrics["cantillation_mean_leaf_depth"] == "2.25"
    assert metrics["cantillation_colless"] == 3
    assert metrics["cantillation_colless_normalized"] == "1"
    assert metrics["cantillation_sackin"] == 9
    assert metrics["cantillation_longest_ladder"] == 2
    assert metrics["cantillation_longest_accent_run"] == 4
    assert metrics["cantillation_depth_leaf_ratio"] == "0.75"


def test_single_leaf_tree_has_zero_shape_indices():
    metrics = tree_features(leaf("Sof Pasuq"))
    assert metrics["cantillation_shape"] == "L"
    assert metrics["cantillation_branch_signature"] == "L"
    assert metrics["cantillation_accent_signature"] == "Sof_Pasuq"
    assert metrics["cantillation_depth"] == 0
    assert metrics["cantillation_mean_leaf_depth"] == "0"
    assert metrics["cantillation_colless_normalized"] == "0"
    assert metrics["cantillation_depth_leaf_ratio"] == "0"
