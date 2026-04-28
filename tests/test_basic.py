# tests/test_basic.py
# Tests ultra-simples pour vérifier que le CI fonctionne

def test_python_works():
    """Vérifie que Python fonctionne (test de base)."""
    assert 1 + 1 == 2


def test_string_operations():
    """Vérifie les opérations sur les chaînes."""
    text = "CV Evaluator"
    assert "CV" in text
    assert text.lower() == "cv evaluator"


def test_list_operations():
    """Vérifie les opérations sur les listes."""
    items = [1, 2, 3]
    assert len(items) == 3
    assert 2 in items


def test_dictionary_operations():
    """Vérifie les opérations sur les dictionnaires."""
    data = {"score": 85, "max": 100}
    assert data["score"] == 85
    assert "max" in data


def test_import_standard_library():
    """Vérifie que les bibliothèques standard sont disponibles."""
    import json
    import os
    import sys
    
    assert json is not None
    assert os is not None
    assert sys is not None