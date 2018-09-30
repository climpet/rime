#!/usr/bin/python

import os
import os.path

from rime.basic import consts
import rime.basic.targets.problem  # NOQA
import rime.basic.targets.project  # NOQA
import rime.basic.targets.testset  # NOQA
from rime.core import commands
from rime.core import targets
from rime.core import taskgraph
from rime.util import files


_PACKED_TARBALL_TEMPLATE = '%s.tar.gz'


class Project(targets.registry.Project):
    @taskgraph.task_method
    def Pack(self, ui):
        results = yield taskgraph.TaskBranch(
            [problem.Pack(ui) for problem in self.problems])
        yield all(results)


class Problem(targets.registry.Problem):
    @taskgraph.task_method
    def Pack(self, ui):
        results = yield taskgraph.TaskBranch(
            [testset.Pack(ui) for testset in self.testsets])
        yield all(results)


class Testset(targets.registry.Testset):
    def __init__(self, *args, **kwargs):
        super(Testset, self).__init__(*args, **kwargs)
        self.pack_dir = os.path.join(self.out_dir, 'pack')

    @taskgraph.task_method
    def Pack(self, ui):
        if not (yield self.Build(ui)):
            yield False
        testcases = self.ListTestCases()
        ui.console.PrintAction('PACK', self, progress=True)
        try:
            files.RemoveTree(self.pack_dir)
            files.MakeDir(self.pack_dir)
        except Exception:
            ui.errors.Exception(self)
            yield False
        for (i, testcase) in enumerate(testcases):
            basename = os.path.splitext(testcase.infile)[0]
            difffile = basename + consts.DIFF_EXT
            packed_infile = str(i + 1) + consts.IN_EXT
            packed_difffile = str(i + 1) + consts.DIFF_EXT
            try:
                ui.console.PrintAction(
                    'PACK',
                    self,
                    '%s -> %s' % (testcase.infile, packed_infile),
                    progress=True)
                files.CopyFile(os.path.join(self.out_dir, testcase.infile),
                               os.path.join(self.pack_dir, packed_infile))
                ui.console.PrintAction(
                    'PACK',
                    self,
                    '%s -> %s' % (difffile, packed_difffile),
                    progress=True)
                files.CopyFile(os.path.join(self.out_dir, difffile),
                               os.path.join(self.pack_dir, packed_difffile))
            except Exception:
                ui.errors.Exception(self)
                yield False
        tarball_filename = _PACKED_TARBALL_TEMPLATE % self.name
        tar_args = ('tar', 'czf',
                    os.path.join(os.pardir, os.pardir, tarball_filename),
                    os.curdir)
        ui.console.PrintAction(
            'PACK',
            self,
            ' '.join(tar_args),
            progress=True)
        devnull = files.OpenNull()
        task = taskgraph.ExternalProcessTask(
            tar_args, cwd=self.pack_dir,
            stdin=devnull, stdout=devnull, stderr=devnull)
        try:
            proc = yield task
        except Exception:
            ui.errors.Exception(self)
            yield False
        ret = proc.returncode
        if ret != 0:
            ui.errors.Error(self, 'tar failed: ret = %d' % ret)
            yield False
        ui.console.PrintAction(
            'PACK',
            self,
            tarball_filename)
        yield True


targets.registry.Override('Project', Project)
targets.registry.Override('Problem', Problem)
targets.registry.Override('Testset', Testset)


class Pack(commands.CommandBase):
    def __init__(self, parent):
        super(Pack, self).__init__(
            'pack',
            '',
            'Pack testsets to export to M-judge. (pack_mjudge plugin)',
            '',
            parent)

    def Run(self, obj, args, ui):
        """Entry point for pack command."""
        if args:
            ui.console.PrintError('Extra argument passed to pack command!')
            return None

        if isinstance(obj, (Project, Problem, Testset)):
            return obj.Pack(ui)

        ui.console.PrintError(
            'Pack is not supported for the specified target.')
        return None


commands.registry.Add(Pack)
