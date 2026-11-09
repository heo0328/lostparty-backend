"""Local synthetic guard checks. No DB, live archive, key or provider is used."""
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from scripts.recruitment_restore_preflight import compare,PreflightError,require_checkpoint_state
from scripts.recruitment_snapshot import extract_keys


class PreservationGuards(unittest.TestCase):
    def test_checkpoint_never_claims_a_running_api_is_quiesced(self):
        require_checkpoint_state({'State':{'Running':True}},False)
        require_checkpoint_state({'State':{'Running':False}},True)
        with self.assertRaises(PreflightError):require_checkpoint_state({'State':{'Running':True}},True)

    def test_restore_rejects_changed_row_or_record_clock(self):
        original={'records':dict(rows=2,sha256='original-including-record-clocks',columns=['id','record_updated_at'])}
        with self.assertRaises(PreflightError):
            compare(original,{'records':original['records']|dict(sha256='changed-clock')})
        with self.assertRaises(PreflightError):
            compare(original,{'records':original['records']|dict(rows=1)})

    def test_restore_rejects_missing_table_or_changed_columns(self):
        original={'records':dict(rows=2,sha256='synthetic',columns=['id','record_updated_at'])}
        with self.assertRaises(PreflightError):compare(original,{})
        with self.assertRaises(PreflightError):compare(original,{'records':original['records']|dict(columns=['id'])})

    def test_additive_migration_only_allows_new_tables_and_version_change(self):
        original={'records':dict(rows=2,sha256='synthetic'), 'alembic_version':dict(rows=1,sha256='23')}
        migrated={**original,'new_table':dict(rows=1,sha256='new'),'alembic_version':dict(rows=1,sha256='29')}
        compare(original,migrated,migration=True)
        with self.assertRaises(PreflightError):compare(original,migrated)
        with self.assertRaises(PreflightError):compare(original,migrated|dict(records=dict(rows=0,sha256='changed')),migration=True)


class KeyArchiveGuards(unittest.TestCase):
    def archive(self,root,name,*,link=False):
        p=Path(root)/'synthetic.tar'
        with tarfile.open(p,'w') as archive:
            member=tarfile.TarInfo(name)
            if link:member.type=tarfile.SYMTYPE;member.linkname='../escape'
            else:member.size=4
            archive.addfile(member,None if link else io.BytesIO(b'test'))
        return p

    def test_extract_keeps_bytes_private_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,AUTH_SECRET_DIR=root+'/keys'):
            p=self.archive(root,'synthetic.key');extract_keys(p)
            key=Path(root)/'keys/synthetic.key'
            self.assertEqual(key.read_bytes(),b'test');self.assertEqual(key.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):extract_keys(p)
            self.assertEqual(key.read_bytes(),b'test')

    def test_extract_rejects_path_traversal_and_absolute_paths(self):
        for name in ('../escape','/escape'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as root,patch.dict(os.environ,AUTH_SECRET_DIR=root+'/keys'):
                with self.assertRaises(RuntimeError):extract_keys(self.archive(root,name))
                self.assertFalse((Path(root)/'escape').exists())

    def test_extract_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,AUTH_SECRET_DIR=root+'/keys'):
            with self.assertRaises(RuntimeError):extract_keys(self.archive(root,'synthetic.key',link=True))
            self.assertFalse((Path(root)/'keys/synthetic.key').exists())


if __name__=='__main__':unittest.main()
