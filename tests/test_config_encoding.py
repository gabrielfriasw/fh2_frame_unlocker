import codecs
import tempfile
import unittest
from pathlib import Path
import engine


class ConfigEncodingTests(unittest.TestCase):
    def test_unicode_formats_preserve_values_and_file(self):
        text = "[settings]\r\n; comment\r\ngame_folder=D:\\Jogos\\Corrida São Paulo_日本\r\nframe_rate=90\r\n"
        formats = [(b'', 'utf-8'), (codecs.BOM_UTF8, 'utf-8'),
                   (codecs.BOM_UTF16_LE, 'utf-16-le'), (codecs.BOM_UTF16_BE, 'utf-16-be'),
                   (codecs.BOM_UTF32_LE, 'utf-32-le'), (codecs.BOM_UTF32_BE, 'utf-32-be')]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'azimuth.ini'
            for bom, encoding in formats:
                with self.subTest(encoding=encoding, bom=bom):
                    original = bom + text.encode(encoding)
                    path.write_bytes(original)
                    values = engine.config_values(path)
                    self.assertEqual(values['game_folder'], 'D:\\Jogos\\Corrida São Paulo_日本')
                    self.assertEqual(values['frame_rate'], '90')
                    self.assertEqual(path.read_bytes(), original)

    def test_detect_game_reads_utf16_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').mkdir()
            (root/'game'/'Mount').mkdir(parents=True)
            (root/'game'/'Mount'/engine.GAME_NAME).write_bytes(b'fixture')
            (root/'data'/'azimuth.ini').write_text('game_folder=game\n', encoding='utf-16')
            self.assertEqual(engine.detect_game(root), str((root/'game').resolve()))

    def test_invalid_input_is_rejected_without_data_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'azimuth.ini'
            for raw in [b'\xff', b'\xff\xfex', 'frame_rate=90'.encode('utf-16-le')]:
                with self.subTest(raw=raw):
                    path.write_bytes(raw)
                    with self.assertRaises(RuntimeError):
                        engine.config_values(path)
                    self.assertEqual(path.read_bytes(), raw)

    def test_duplicate_keys_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'azimuth.ini'
            path.write_text('frame_rate=60\nframe_rate=90\n', encoding='utf-16')
            with self.assertRaises(RuntimeError):
                engine.config_values(path)
