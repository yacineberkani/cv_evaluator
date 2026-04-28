# tests/test_basic.py
# Tests basiques pour vérifier que le projet fonctionne

import pytest


class TestBasicImports:
    """Test que les modules principaux peuvent être importés."""
    
    def test_import_models(self):
        """Test l'importation du module models."""
        from models import schemas
        assert schemas is not None
    
    def test_import_utils(self):
        """Test l'importation du module utils."""
        from utils import pdf_parser, chunking, cache
        assert pdf_parser is not None
        assert chunking is not None
        assert cache is not None
    
    def test_import_prompts(self):
        """Test l'importation du module prompts."""
        from prompts import templates
        assert templates is not None


class TestSchemas:
    """Test les modèles Pydantic."""
    
    def test_schemas_has_models(self):
        """Vérifie que schemas.py contient les modèles attendus."""
        from models.schemas import (
            ExperienceAnalysis,
            SkillsEducationAnalysis,
            ScoringResult,
            FinalReport
        )
        assert ExperienceAnalysis is not None
        assert SkillsEducationAnalysis is not None
        assert ScoringResult is not None
        assert FinalReport is not None


class TestPDFParser:
    """Test le parseur PDF."""
    
    def test_pdf_parser_has_extract_function(self):
        """Vérifie que pdf_parser a une fonction d'extraction."""
        from utils.pdf_parser import extract_text_from_pdf
        assert callable(extract_text_from_pdf)
    
    def test_pdf_parser_returns_none_for_invalid_path(self):
        """Vérifie qu'un chemin invalide retourne une erreur gérée."""
        from utils.pdf_parser import extract_text_from_pdf
        result = extract_text_from_pdf("/chemin/inexistant.pdf")
        # Le comportement exact dépend de ton implémentation
        # Adapte ce test en conséquence