"""Apply one development lease scope to each initialized pytest test call."""
from contextlib import ExitStack
from hashlib import sha256

import pytest


class LeasePlugin:
    def __init__(self,activate,record,terminal):
        self.activate=activate;self.record=record;self.terminal=terminal
        terminal['pytest_test_calls']=[];terminal['pytest_reports']=[]
        terminal['pytest_call_outcomes']={key:0 for key in ('passed','failed','skipped')}

    @pytest.hookimpl(hookwrapper=True,tryfirst=True)
    def pytest_runtest_call(self,item):
        prefix=sha256(item.nodeid.encode()).hexdigest()+'_'
        row=dict(nodeid=item.nodeid,receipt_prefix=prefix,scope_entered=False,scope_exited=False)
        self.terminal['pytest_test_calls'].append(row)
        try:
            with ExitStack() as stack:
                code,parsed=self.activate(stack);row['scope_entered']=True
                yield
                self.record(code,parsed,prefix,item.nodeid)
            row['scope_exited']=True
        except BaseException:
            row['scope_error']=True
            raise

    def pytest_runtest_logreport(self,report):
        self.terminal['pytest_reports'].append(dict(nodeid=report.nodeid,phase=report.when,outcome=report.outcome))
        if report.when=='call':self.terminal['pytest_call_outcomes'][report.outcome]+=1

    def pytest_sessionfinish(self,session,exitstatus):
        self.terminal.update(pytest_tests_collected=session.testscollected,pytest_tests_failed=session.testsfailed)
