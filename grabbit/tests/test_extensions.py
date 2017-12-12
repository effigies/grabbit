import pytest
from grabbit import WritableFile, WritableLayout
import os
import shutil
from os.path import join, exists, islink, dirname


@pytest.fixture
def writable_file(tmpdir):
    testfile = 'sub-03_ses-2_task-rest_acq-fullbrain_run-2_bold.nii.gz'
    fn = tmpdir.mkdir("tmp").join(testfile)
    fn.write('###')
    return WritableFile(os.path.join(str(fn)))


class TestWritableFile:

    def test_build_path(self, writable_file):
        writable_file.entities = {'task': 'rest', 'run': '2', 'subject': '3'}

        # Single simple pattern
        with pytest.raises(ValueError):
            writable_file.build_path()
        pat = join(writable_file.dirname, '{task}/sub-{subject}/run-{run}.nii.gz')
        target = join(writable_file.dirname, 'rest/sub-3/run-2.nii.gz')
        assert writable_file.build_path(pat) == target
        writable_file.path_patterns = pat
        assert writable_file.build_path() == target

        # Multiple simple patterns
        pats = ['{session}/{task}/r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz',
                '{subject}/{task}.nii.gz']
        pats = [join(writable_file.dirname, p) for p in pats]
        target = join(writable_file.dirname, 't-rest/3-2.nii.gz')
        assert writable_file.build_path(pats) == target

        # Pattern with optional entity
        pats = ['[{session}/]{task}/r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz']
        pats = [join(writable_file.dirname, p) for p in pats]
        target = join(writable_file.dirname, 'rest/r-2.nii.gz')
        assert writable_file.build_path(pats) == target

    def test_build_file(self, writable_file, tmpdir, caplog):
        writable_file.entities = {'task': 'rest', 'run': '2', 'subject': '3'}

        # Simple write out
        new_dir = join(writable_file.dirname, 'rest')
        pat = join(writable_file.dirname, '{task}/sub-{subject}/run-{run}.nii.gz')
        target = join(writable_file.dirname, 'rest/sub-3/run-2.nii.gz')
        writable_file.build_file(pat)
        assert exists(target)

        # Conflict handling
        with pytest.raises(ValueError):
            writable_file.build_file(pat)
        with pytest.raises(ValueError):
            writable_file.build_file(pat, conflicts='fail')
        writable_file.build_file(pat, conflicts='skip')
        log_message = caplog.records[0].message
        assert log_message == 'A file at path {} already exists, ' \
                              'skipping writing file.'.format(target)
        writable_file.build_file(pat, conflicts='append')
        append_target = join(writable_file.dirname, 'rest/sub-3/run-2_1.nii.gz')
        assert exists(append_target)
        writable_file.build_file(pat, conflicts='overwrite')
        assert exists(target)
        shutil.rmtree(new_dir)

        # Symbolic linking
        writable_file.build_file(pat, symbolic_link=True)
        assert islink(target)
        shutil.rmtree(new_dir)

        # Using different root
        root = str(tmpdir.mkdir('tmp2'))
        pat = join(root, '{task}/sub-{subject}/run-{run}.nii.gz')
        target = join(root, 'rest/sub-3/run-2.nii.gz')
        writable_file.build_file(pat, root=root)
        assert exists(target)

        # Copy into directory functionality
        pat = join(writable_file.dirname, '{task}/')
        writable_file.build_file(pat)
        target = join(writable_file.dirname, 'rest', writable_file.filename)
        assert exists(target)
        shutil.rmtree(new_dir)


class TestWritableLayout:

    def test_write_files(self, tmpdir):
        data_dir = join(dirname(__file__), 'data', '7t_trt')
        config = join(dirname(__file__), 'specs', 'test.json')
        layout = WritableLayout(data_dir, config=config)
        pat = join(str(tmpdir), 'sub-{subject}'
                                '/sess-{session}'
                                '/r-{run}'
                                '/type-{type}'
                                '/task-{task}.nii.gz')
        layout.write_files(path_patterns=pat)
        example_file = join(str(tmpdir), 'sub-02'
                                         '/sess-2'
                                         '/r-1'
                                         '/type-bold'
                                         '/task-rest_acq.nii.gz')
        assert exists(example_file)

    def test_write_contents_to_file(self):
        contents = 'test'
        data_dir = join(dirname(__file__), 'data', '7t_trt')
        config = join(dirname(__file__), 'specs', 'test.json')
        layout = WritableLayout(data_dir, config=config)
        entities = {'subject': 'Bob', 'session': '01'}
        pat = join('sub-{subject}/sess-{session}/desc.txt')
        layout.write_contents_to_file(entities, path_patterns=pat,
                                      contents=contents)
        target = join(data_dir, 'sub-Bob/sess-01/desc.txt')
        assert exists(target)
        with open(target) as f:
            written = f.read()
        assert written == contents
        assert target in layout.files
        shutil.rmtree(join(data_dir, 'sub-Bob'))

    def test_write_contents_to_file_defaults(self):
        contents = 'test'
        data_dir = join(dirname(__file__), 'data', '7t_trt')
        config = join(dirname(__file__), 'specs', 'test.json')
        layout = WritableLayout(data_dir, config=config)
        entities = {'subject': 'Bob', 'session': '01', 'run': '1',
                    'type': 'test', 'task': 'test', 'acquisition': 'test',
                    'bval': 0}
        layout.write_contents_to_file(entities, contents=contents)
        target = join(data_dir, 'sub-Bob/ses-01/Bob011testtesttest0')
        assert exists(target)
        with open(target) as f:
            written = f.read()
        assert written == contents
        assert target in layout.files
        shutil.rmtree(join(data_dir, 'sub-Bob'))
