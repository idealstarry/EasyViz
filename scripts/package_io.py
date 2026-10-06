"""Bounded file hashing and rollback for explicitly owned package outputs."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import shutil
import tempfile


class OutputRollbackError(RuntimeError):
    """A failed rollback retains the staging directory for manual recovery."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def staging_directory(parent: Path, prefix: str):
    """Keep recovery bytes if publication could not restore an old output."""
    folder = Path(tempfile.mkdtemp(dir=parent, prefix=prefix))
    recover = False
    try:
        yield folder
    except OutputRollbackError:
        recover = True
        raise
    finally:
        if not recover:
            shutil.rmtree(folder)


def replace_outputs(replacements, staging: Path, check_target) -> None:
    """Publish sibling owned leaves; restore all prior leaves on failure.

    Callers retain responsibility for destination ownership and types. Sources
    are complete staged files/directories on the same filesystem as targets.
    Only the enumerated leaves are replaced; unrelated siblings stay intact.
    """
    replacements = list(replacements)
    for source, target in replacements:
        check_target(target)
        if source.is_symlink() or not (source.is_file() or source.is_dir()):
            raise ValueError(f'Invalid staged package output: {source}')
    backup = staging / 'rollback'
    backup.mkdir()
    changed = []
    try:
        for index, (source, target) in enumerate(replacements):
            check_target(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            previous = backup / str(index)
            if target.exists():
                target.replace(previous)
            changed.append((target, previous))
            source.replace(target)
    except BaseException as error:
        failures = []
        for target, previous in reversed(changed):
            try:
                check_target(target)
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink(missing_ok=True)
                if previous.exists():
                    previous.replace(target)
            except (OSError, ValueError) as failure:
                failures.append(f'{target}: {failure}')
        if failures:
            raise OutputRollbackError(f'Package rollback failed; recovery retained at {staging}: '
                                      + '; '.join(failures)) from error
        raise
