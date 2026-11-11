"""Contracts for project-local agent definitions; runtime delegation is tested separately."""
from pathlib import Path
import unittest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: CI also runs 3.11 with tomllib.
    tomllib = None

ROOT = Path(__file__).resolve().parents[1]
ROLES = {'datos', 'geoespacial', 'backend', 'operaciones', 'calidad', 'interfaz', 'seguridad'}


@unittest.skipIf(tomllib is None, 'TOML parser is included with Python 3.11+')
class AgencyConfiguration(unittest.TestCase):
    def test_roles_resolve_and_have_actionable_contracts(self):
        config_dir = ROOT / '.codex'
        config = tomllib.loads((config_dir / 'config.toml').read_text(encoding='utf-8'))
        agents = config['agents']
        self.assertTrue(1 <= agents['max_threads'] <= 7)
        self.assertEqual(ROLES, set(agents) - {'max_threads'})
        for name in ROLES:
            with self.subTest(role=name):
                path = (config_dir / agents[name]['config_file']).resolve()
                self.assertTrue(path.is_relative_to(config_dir.resolve()))
                instruction = tomllib.loads(path.read_text(encoding='utf-8'))['developer_instructions']
                for section in ('MISIÓN:', 'TRABAJO:', 'ENTREGA:', 'REFERENCIA DE DISEÑO:'):
                    self.assertIn(section, instruction)
                self.assertIn('UNKNOWN', instruction)
                self.assertIn('secretos', instruction.lower())
