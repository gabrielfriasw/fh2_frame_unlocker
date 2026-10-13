import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import engine


class DirectLaunchTests(unittest.TestCase):
    def test_setup_preserves_installation_and_backup_uses_live_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime, game, profile = root/'azimuth', root/'game', root/'profile'
            (runtime/'data'/'saves').mkdir(parents=True)
            game.mkdir()
            exe = runtime/'azimuth.exe'
            exe.write_bytes(b'fixture executable')
            ini = runtime/'data'/'azimuth.ini'
            ini.write_text('frame_rate=90\nframe_pacing=real-time\n')
            save = runtime/'data'/'saves'/'progress'
            save.write_bytes(b'first save')
            before = engine.tree_hashes(runtime)
            with patch.object(engine, 'running_azimuth', return_value=[]), patch.object(engine, 'inspect_installation', return_value=(exe, game)), patch.object(engine, 'detect_game', return_value=str(game)):
                engine.prepare(exe, game, profile)
                state, values = engine.validate_profile(profile)
            self.assertEqual(before, engine.tree_hashes(runtime))
            self.assertFalse((profile/'runtime').exists())
            self.assertEqual(engine.runtime_path(profile), runtime)
            self.assertEqual(values['frame_rate'], '90')
            self.assertEqual((profile/'save-backups'/'initial'/'saves'/'progress').read_bytes(), b'first save')
            save.write_bytes(b'new progress')
            engine.snapshot_saves(profile, 'next-launch')
            self.assertEqual((profile/'save-backups'/'next-launch'/'saves'/'progress').read_bytes(), b'new progress')

    def test_legacy_profile_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp)
            engine.write_json(profile/'profile.json', {'format': 'fh2-fps-unlocker-v1'})
            with self.assertRaisesRegex(RuntimeError, 'Run setup'):
                engine.runtime_path(profile)
